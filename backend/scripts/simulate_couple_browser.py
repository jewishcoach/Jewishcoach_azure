"""
Browser check of the couple screens: real frontend (vite dev) + real backend (uvicorn, temp SQLite), two demo users
(dev-only bypass, localStorage e2e_demo_user) whose conversations are seeded at the end of discovery — so the screens
are exercised without running two whole coaching processes. Run from backend/:
    .venv/bin/python -u scripts/simulate_couple_browser.py [--headed]
Covers: preview with a hidden line → waiting → the partner's approval opens the mirror (mobile), polling opens it for
the one waiting, the hidden line never reaches the partner, כמ"ז opens after the mirror, the join screen of an invite
link. Screenshots go to /tmp/couple_browser/.
"""
import os, sys, json, time, argparse, subprocess, signal, tempfile, urllib.request
from datetime import datetime, timezone

_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["DATABASE_URL"] = f"sqlite:///{_db}"
sys.path.insert(0, os.getcwd())

from playwright.sync_api import sync_playwright  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from app.database import Base, engine  # noqa: E402
import app.models  # noqa: E402,F401
from app.models import Conversation, CoupleMember, CoupleSession, Message, User  # noqa: E402
from app.services import couple_service as cs  # noqa: E402

FRONTEND_DIR = os.path.join(os.path.dirname(os.getcwd()), "frontend")
# Other sessions run their own dev servers (simulate_v3_browser_flow.py: 8000/5173 or SIM_* ports) — own defaults here,
# and a busy port stops the run instead of photographing another branch
BACKEND_PORT = int(os.getenv("SIM_BACKEND_PORT", "8020"))
FRONTEND_PORT = int(os.getenv("SIM_FRONTEND_PORT", "5176"))
APP = f"http://localhost:{FRONTEND_PORT}"
OUT = "/tmp/couple_browser"
TITLE = "הוויכוח על ההוצאות, מוצאי שבת"

NOA = {
    "emotions": ["חרדה", "כעס", "בדידות"], "thought": "אני לבד עם כל הדאגות",
    "action_actual": "הרמתי את הקול ודרשתי שיענה לי", "emotion_desired": "שקט וביטחון",
    "action_desired": "לבקש לשבת יחד בזמן שמתאים לשנינו",
    "pattern": "להגיב בחוסר סבלנות ובהגנה כשאת מרגישה שלא מקשיבים לך",
    "paradigm": "ככה זה אצלי — אם לא אגן על עצמי בחוזקה, אף אחד לא יתייחס אליי ברצינות",
    "stance": {"short": "אם לא אעמוד על שלי בחוזקה, לא יכבדו אותי",
               "activation_trigger": "כשמתעלמים ממני או לא עונים לי", "gains": ["שומעים אותי"], "losses": ["ריחוק"]},
}
ITAI = {
    "emotions": ["תסכול", "חוסר אונים"], "thought": "אני צריך שקט, אחרת אני טובע",
    "action_actual": "שתקתי וקמתי לחדר השני", "pattern": "להיסגר ולשתוק",
    "paradigm": "ככה זה אצלי — שקט מגן עליי מהצפה",
    "stance": {"short": "כשאני שקט, אני מונע מהמצב להחמיר", "activation_trigger": "כשמדברים אליי בטון גבוה",
               "gains": ["שקט"], "losses": ["ניתוק"]},
}


def wait_http(url, timeout=90):
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(url, timeout=3)
            return True
        except Exception as e:
            if getattr(e, "code", None):
                return True
            time.sleep(1)
    return False


def seed():
    """Two members at the end of discovery, plus an open invite for a third user (join screen)."""
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc)
    users = {}
    for key, name, gender in (("a", "נועה", "female"), ("b", "איתי", "male"), ("c", "דנה", "female")):
        users[key] = User(clerk_id=f"demo_user_tunnel_{key}", email=f"demo+{key}@tunnel.test", display_name=name,
                          gender=gender, created_at=now)
        db.add(users[key])
    db.flush()

    session = CoupleSession(event_title=TITLE, status="active")
    db.add(session)
    db.flush()
    for key, role, cd in (("a", "inviter", NOA), ("b", "invitee", ITAI)):
        conv = cs.create_member_conversation(db, users[key], session, role)
        state = dict(conv.v2_state)
        state["current_step"] = "S11"
        state["collected_data"] = {**state["collected_data"], **cd}
        state["messages"] = [{"sender": "user", "content": "תהליך זוגי — האירוע: " + TITLE, "timestamp": now.isoformat()},
                             {"sender": "coach", "content": "מצד אחד העמדה נותנת לך משהו — מצד שני היא עולה לך. יש פה מתח אמיתי.",
                              "timestamp": now.isoformat(), "internal_state": {"current_step": "S11", "stage_ready_to_complete": True}}]
        conv.v2_state = state
        conv.current_phase = "S11"
        for i in range(3):  # the app resumes a conversation with a few user messages (welcome back)
            db.add(Message(conversation_id=conv.id, role="user", content=f"הודעה {i}", timestamp=now))
        db.add(CoupleMember(session_id=session.id, user_id=users[key].id, conversation_id=conv.id, role=role,
                            display_name=users[key].display_name, gender=users[key].gender))

    invited = CoupleSession(event_title="מה שקרה בארוחה אצל ההורים", status="invited")
    db.add(invited)
    db.flush()
    token = cs.new_invite_token(invited)
    conv = cs.create_member_conversation(db, users["a"], invited, "inviter")
    db.add(CoupleMember(session_id=invited.id, user_id=users["a"].id, conversation_id=conv.id, role="inviter",
                        display_name="נועה", gender="female"))
    db.commit()
    sid = session.id
    db.close()
    return sid, token


def _port_busy(port):
    import socket
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", port)) == 0


def start_servers():
    for port in (BACKEND_PORT, FRONTEND_PORT):
        if _port_busy(port):
            sys.exit(f"port {port} is in use (another session's server?) — set SIM_BACKEND_PORT / SIM_FRONTEND_PORT")
    env = dict(os.environ, ALLOW_DEMO_MODE="true", ALLOW_DEMO_LOCALHOST="true", COUPLE_PILOT_EMAILS="*",
               CORS_ORIGINS=f"http://localhost:{FRONTEND_PORT}")
    be = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(BACKEND_PORT)], env=env,
                          stdout=open(f"{OUT}/backend.log", "w"), stderr=subprocess.STDOUT, start_new_session=True)
    fe = subprocess.Popen(["npm", "run", "dev", "--", "--port", str(FRONTEND_PORT), "--strictPort"], cwd=FRONTEND_DIR,
                          env=dict(os.environ, VITE_API_URL=f"http://localhost:{BACKEND_PORT}"),
                          stdout=open(f"{OUT}/frontend.log", "w"), stderr=subprocess.STDOUT, start_new_session=True)
    if not wait_http(f"http://localhost:{BACKEND_PORT}/docs") or not wait_http(f"{APP}/"):
        stop(be, fe)
        sys.exit(f"servers did not start — see {OUT}/backend.log / frontend.log")
    return be, fe


def stop(*procs):
    for p in procs:
        try:
            os.killpg(p.pid, signal.SIGTERM)
        except Exception:
            pass


def open_as(browser, key, url, mobile=False, devices=None):
    kwargs = dict(devices["iPhone 13"]) if mobile else {"viewport": {"width": 1280, "height": 900}}
    ctx = browser.new_context(locale="he-IL", **kwargs)
    ctx.add_init_script(f"localStorage.setItem('e2e_demo','true');localStorage.setItem('e2e_demo_user','{key}');"
                        "localStorage.setItem('ux_v3','true');")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: errors.append(f"console: {m.text}") if m.type == "error" else None)
    page.on("response", lambda r: errors.append(f"http {r.status}: {r.url[:120]}") if r.status >= 400 else None)
    page.goto(url)
    return page, errors


def main(headed):
    os.makedirs(OUT, exist_ok=True)
    sid, token = seed()
    be, fe = start_servers()
    checks, errors = [], []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=not headed)

            a, err_a = open_as(browser, "a", f"{APP}/?v3")
            a.get_by_text("אישרתי — אפשר לשתף").wait_for(timeout=30000)
            checks.append(("A lands on the preview (resumed at the end of discovery)", True))
            checks.append(("pattern line in first person", a.locator("textarea").nth(5).input_value().find("כשאני") >= 0))
            a.wait_for_timeout(500)  # fade-in
            a.screenshot(path=f"{OUT}/a_preview.png", full_page=True)
            a.get_by_role("button", name="להסתיר").first.click()  # hide "מה הרגשתי"
            a.get_by_text("השורה הזו לא תוצג").wait_for(timeout=5000)
            a.get_by_text("אישרתי — אפשר לשתף").click()
            a.get_by_text("החלק שלך הסתיים").wait_for(timeout=15000)
            a.wait_for_timeout(500)
            a.screenshot(path=f"{OUT}/a_waiting.png", full_page=True)
            checks.append(("A waits after approving", True))

            b, err_b = open_as(browser, "b", f"{APP}/?v3", mobile=True, devices=pw.devices)
            b.get_by_text("אישרתי — אפשר לשתף").wait_for(timeout=30000)
            b.get_by_text("אישרתי — אפשר לשתף").click()
            b.get_by_text("מסך השיתוף").first.wait_for(timeout=15000)
            b.get_by_text("גלגלי השיניים").wait_for(timeout=5000)
            b.wait_for_timeout(500)
            b.screenshot(path=f"{OUT}/b_mirror_mobile.png", full_page=True)
            b.get_by_text("גלגלי השיניים").scroll_into_view_if_needed()
            b.screenshot(path=f"{OUT}/b_gears_mobile.png")
            body_b = b.inner_text("body")
            checks.append(("B's mirror opens on approval, with the gears", True))
            checks.append(("A's hidden line never reaches B", "חרדה, כעס, בדידות" not in body_b))
            checks.append(("B sees A's button", "כשמתעלמים ממני או לא עונים לי" in body_b))

            a.get_by_text("מסך השיתוף").first.wait_for(timeout=25000)  # polling every 15s
            a.wait_for_timeout(500)
            a.screenshot(path=f"{OUT}/a_mirror.png", full_page=True)
            checks.append(("A's waiting screen opens the mirror by itself", True))

            a.get_by_text("להמשך התהליך שלי").click()
            a.get_by_text("מכין את השלב הבא").wait_for(timeout=10000)
            checks.append(("after the mirror, the כמ\"ז intro is requested (hold released)", True))
            time.sleep(20)  # the intro questions are an LLM call
            a.screenshot(path=f"{OUT}/a_after_mirror.png", full_page=True)

            c, err_c = open_as(browser, "c", f"{APP}/?v3&couple={token}", mobile=True, devices=pw.devices)
            c.get_by_text("הזמינה אותך לעבוד יחד על אירוע שחוויתם").wait_for(timeout=30000)
            checks.append(("invite link opens the join screen (token kept through load)", "couple=" not in c.url))
            c.wait_for_timeout(500)
            c.screenshot(path=f"{OUT}/c_join_mobile.png", full_page=True)

            errors = err_a + err_b + err_c
            browser.close()
    except Exception as e:
        checks.append((f"FAILED: {type(e).__name__}: {str(e)[:200]}", False))
    finally:
        stop(be, fe)

    print("\nCHECKS:")
    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'} {name}")
    noisy = [e for e in errors if "favicon" not in e]
    print(f"\nJS errors ({len(noisy)}):")
    for e in noisy[:15]:
        print("  ", e[:200])
    print(f"\nscreenshots: {OUT}/  db {_db}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    main(ap.parse_args().headed)
