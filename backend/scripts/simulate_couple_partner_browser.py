"""
Browser run of the INVITED partner, as a real phone user: opens the invite link, joins, and goes through the cards with
the LLM sim-user (simulate_v3_browser_flow.Driver) up to a given step. Run from backend/ (alone — Azure quota):
    .venv/bin/python -u scripts/simulate_couple_partner_browser.py [--until S8] [--headed]
Screenshots + flags: /tmp/couple_partner_browser/.
"""
import os, sys, argparse

os.environ.setdefault("SIM_BACKEND_PORT", "8020")
os.environ.setdefault("SIM_FRONTEND_PORT", "5176")
os.environ.setdefault("CORS_ORIGINS", f"http://localhost:{os.environ['SIM_FRONTEND_PORT']}")
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
import simulate_v3_browser_flow as bf  # noqa: E402  (ports from SIM_*; sim = its LLM sim-user + temp DB)
from simulate_v3_browser_flow import sim  # noqa: E402
from app.models import CoupleMember, CoupleSession, User  # noqa: E402
from app.services import couple_service as cs  # noqa: E402

OUT = "/tmp/couple_partner_browser"
TITLE = "הוויכוח על ההוצאות, מוצאי שבת"
sim.PERSONAS["couple_partner"] = (
    "נועה", "female", "זוגיות", "כעס",
    "במוצאי שבת ביקשתי מאיתי לשבת על החיובים בכרטיס. הוא אמר 'לא עכשיו' והמשיך בטלפון, הרמתי את הקול והוא יצא מהחדר",
    "נשואה 8 שנים, מרגישה שהיא נושאת לבד את הדאגה לכסף")


def seed():
    """An open shared event from the inviter (who hasn't started) — the partner joins through the link."""
    sim.Base.metadata.create_all(bind=sim.engine)
    db = sim.sessionmaker(bind=sim.engine)()
    now = sim.datetime.now(sim.timezone.utc)
    inviter = User(clerk_id="demo_user_tunnel_a", email="demo+a@tunnel.test", display_name="איתי", gender="male", created_at=now)
    partner = User(clerk_id="demo_user_tunnel_b", email="demo+b@tunnel.test", display_name="נועה", gender="female", created_at=now)
    db.add_all([inviter, partner])
    db.flush()
    session = CoupleSession(event_title=TITLE, status="invited")
    db.add(session)
    db.flush()
    token = cs.new_invite_token(session)
    conv = cs.create_member_conversation(db, inviter, session, "inviter")
    db.add(CoupleMember(session_id=session.id, user_id=inviter.id, conversation_id=conv.id, role="inviter",
                        display_name="איתי", gender="male"))
    db.commit()
    db.close()
    return token


def main(until, headed, max_turns):
    os.makedirs(OUT, exist_ok=True)
    token = seed()
    be, fe = bf.start_servers(OUT, "female")
    try:
        with bf.sync_playwright() as pw:
            browser = pw.chromium.launch(headless=not headed)
            device = {k: v for k, v in pw.devices["iPhone 13"].items() if k != "default_browser_type"}
            page = browser.new_page(**device, locale="he-IL")
            page.set_default_timeout(15000)
            page.add_init_script("localStorage.setItem('e2e_demo','true');localStorage.setItem('e2e_demo_user','b');"
                                 "localStorage.setItem('ux_v3','true');")
            page.goto(f"http://localhost:{bf.FRONTEND_PORT}/?v3&couple={token}")
            page.get_by_text("להצטרף ולהתחיל").wait_for(timeout=30000)
            page.screenshot(path=f"{OUT}/00_join.png")
            page.get_by_text("להצטרף ולהתחיל").click()
            # the join → first message → event card must finish before Driver.run reloads the page
            page.get_by_text("מתי זה קרה?").wait_for(timeout=90000)

            driver = bf.Driver(page, "couple_partner", OUT)
            driver.mobile = True
            # Driver.run reloads the app first — the joined conversation resumes from the saved session
            order = [f"S{i}" for i in range(16)]
            original_detect = driver.detect

            def detect_until():
                state = original_detect()
                if order.index(driver.step) >= order.index(until) and state != "busy":
                    driver.shot(f"reached_{until}")
                    return "stop"
                return state
            driver.detect = detect_until
            driver.run(max_turns, probe_resume_at="", probe_gibberish_at="")
            print(f"\nreached step {driver.step} (target {until})")
            checks = []

            # pilot Oct 30: she came back in a fresh window — the announced card must come back with the conversation
            fresh = browser.new_page(**device, locale="he-IL")
            fresh.add_init_script("localStorage.setItem('e2e_demo','true');localStorage.setItem('e2e_demo_user','b');"
                                  "localStorage.setItem('ux_v3','true');")
            fresh.goto(f"http://localhost:{bf.FRONTEND_PORT}/?v3")
            fresh.get_by_text("נמשיך מאיפה שעצרנו").click(timeout=30000)
            card_title = {"S7": "לפער הזה?", "S6": "באותו רגע בדיוק", "S3": "מה הרגשת באותו רגע?"}.get(until)
            if card_title:
                try:
                    fresh.get_by_text(card_title).first.wait_for(timeout=20000)
                    checks.append((f"fresh window at {until}: the card is back", True))
                except Exception:
                    checks.append((f"fresh window at {until}: the card is back", False))
            fresh.wait_for_timeout(500)
            fresh.screenshot(path=f"{OUT}/resume_fresh_{until}.png")

            # the inviter never started (app reloaded on the invite screen): the start screen offers his part
            inviter = browser.new_page(**device, locale="he-IL")
            inviter.add_init_script("localStorage.setItem('e2e_demo','true');localStorage.setItem('e2e_demo_user','a');"
                                    "localStorage.setItem('ux_v3','true');")
            inviter.goto(f"http://localhost:{bf.FRONTEND_PORT}/?v3")
            try:
                inviter.get_by_text("התהליך הזוגי שלך מחכה").wait_for(timeout=30000)
                inviter.screenshot(path=f"{OUT}/inviter_banner.png")
                inviter.get_by_text("להתחיל את החלק שלי").click()
                inviter.get_by_text("מתי זה קרה?").wait_for(timeout=90000)
                checks.append(("inviter: banner starts the part → event card", True))
            except Exception as e:
                checks.append((f"inviter: banner starts the part → event card ({type(e).__name__})", False))
            inviter.screenshot(path=f"{OUT}/inviter_started.png")

            # the pilot inviter's real case: his part started (S2) but has too few messages for "welcome back" — the
            # start screen leads back to it, and the event card comes back with the conversation
            again = browser.new_page(**device, locale="he-IL")
            again.add_init_script("localStorage.setItem('e2e_demo','true');localStorage.setItem('e2e_demo_user','a');"
                                  "localStorage.setItem('ux_v3','true');")
            again.goto(f"http://localhost:{bf.FRONTEND_PORT}/?v3")
            try:
                again.get_by_text("להמשיך מאיפה שעצרתי").click(timeout=30000)
                again.get_by_text("מתי זה קרה?").wait_for(timeout=20000)
                checks.append(("inviter back in a fresh window: banner → his conversation with the event card", True))
            except Exception as e:
                checks.append((f"inviter back in a fresh window ({type(e).__name__})", False))
            again.screenshot(path=f"{OUT}/inviter_back.png")
            print("\nCHECKS:")
            for name, ok in checks:
                print(f"  {'✅' if ok else '❌'} {name}")
            browser.close()
    finally:
        bf.stop_servers(be, fe)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--until", default="S8", help="stop once the conversation is at this step")
    ap.add_argument("--max-turns", type=int, default=30)
    ap.add_argument("--headed", action="store_true")
    a = ap.parse_args()
    main(a.until, a.headed, a.max_turns)
