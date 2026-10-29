"""
End-to-end couple process through the REAL endpoints: partner A opens a shared event and invites B; each works
alone to the end of discovery; both approve → mirror screen; each alone to the end of the process; both approve →
commitment screen. Simulated users = two LLM personas with the same event from two sides. Temp SQLite DB.
Run from backend/ (alone — shares the Azure quota with every other E2E run):
    .venv/bin/python -u scripts/simulate_couple_e2e.py
"""
import os, sys, json, re, time, argparse
from datetime import datetime, timezone

os.environ.setdefault("COUPLE_PILOT_EMAILS", "*")
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
import simulate_v3_e2e_flow as sim  # noqa: E402  (sets the temp DATABASE_URL, loads .env, builds the sim-user LLM)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from app.database import Base, engine, get_db  # noqa: E402
from app.models import User  # noqa: E402
from app.dependencies import get_current_user  # noqa: E402
from app.middleware.usage_limiter import require_message_quota  # noqa: E402
from app.main import app  # noqa: E402
from app.bsd_v2.stage_intro_schema import step_to_macro_stage  # noqa: E402

TITLE = "הוויכוח על ההוצאות, מוצאי שבת"
COUPLE = {
    "pursuer": ("נועה", "female", "זוגיות", "כעס",
                "במוצאי שבת ביקשתי מאיתי לשבת על החיובים בכרטיס האשראי. הוא אמר 'לא עכשיו' והמשיך בטלפון, "
                "אני הרמתי את הקול ודרשתי שיענה לי, והוא קם ויצא מהחדר",
                "נשואה 8 שנים, שני ילדים, מרגישה שהיא נושאת לבד את הדאגה לכסף; כשלא עונים לה היא נבהלת ונלחמת"),
    "withdrawer": ("איתי", "male", "זוגיות", "הצפה",
                   "במוצאי שבת נועה התחילה לדבר בטון חריף על החיובים בכרטיס. הרגשתי שאני טובע, אמרתי 'לא עכשיו', "
                   "היא צעקה, ושתקתי וקמתי לחדר השני",
                   "נשוי 8 שנים, מהנדס, גדל בבית עם הרבה צעקות; כשמרימים עליו את הקול הוא נסגר"),
}
sim.STYLES["pursuer"] = ("נסערת. בהתחלה מאשימה את איתי ('הוא תמיד בורח'); כשהמאמן שואל עלייך — מדברת בכנות "
                         "על הפחד שלך שלא שומעים אותך.")
sim.STYLES["withdrawer"] = ("עונה קצר ומאופק, לא אוהב לדבר על רגשות, אומר 'אני פשוט צריך שקט'; כשלוחצים בעדינות "
                            "מודה שהוא מרגיש מוצף ושהשתיקה מגינה עליו.")
# The coach of one partner must never talk about the other partner's inner world as fact
PARTNER_GUESS = re.compile(r"(כנראה|אולי|נראה ש)\s*(הוא|היא|בן הזוג|בת הזוג|איתי|נועה)\s*(מרגיש|מפחד|חושב|רוצה)")


class Partner:
    def __init__(self, key, client, users, current):
        self.key, self.c, self.current = key, client, current
        self.p = COUPLE[key]
        self.user = users[key]
        self.history, self.flags, self.trace = [], [], []
        self.step, self.active_tool, self.last_tool, self.sc = "S0", None, None, None
        self.conv_id = None

    def use(self):
        self.current["user"] = self.user
        sim.STYLE = self.key
        return self.c

    def record(self, resp, kind):
        coach = resp.get("coach_message") or resp.get("opening_message") or ""
        new_step = resp.get("current_step") or self.step
        tool, sc = resp.get("tool_call"), resp.get("stage_complete")
        self.history.append(f"מאמן: {coach}")
        self.trace.append((kind, self.step, new_step, (tool or {}).get("tool_type"), bool(sc), coach))
        print(f"\n[{self.p[0]} {len(self.trace):02d}] {kind:5} {self.step}→{new_step}"
              + (f"  🃏 {tool['tool_type']}" if tool else "") + ("  🏁 STAGE COMPLETE" if sc else ""))
        print(f"     🤖 {coach[:400]}")
        if self.step != "S0" and step_to_macro_stage(new_step) != step_to_macro_stage(self.step) and not sc and kind != "intro":
            self.flags.append(f"[{len(self.trace)}] crossed macro {self.step}→{new_step} without stage_complete")
        if kind != "intro" and self.step != "S0" and int(new_step[1:]) < int(self.step[1:]):
            self.flags.append(f"[{len(self.trace)}] BACKWARD jump {self.step}→{new_step}")
        if PARTNER_GUESS.search(coach):
            self.flags.append(f"[{len(self.trace)}] coach guesses the partner's inner world: {PARTNER_GUESS.search(coach).group(0)}")
        self.step, self.active_tool, self.sc = new_step, tool, sc

    def start(self):
        first = f"תהליך זוגי — האירוע: {TITLE}"
        r = self.use().post("/api/chat/v2/message", json={"message": first, "conversation_id": self.conv_id,
                                                           "language": "he"}, headers=sim_headers())
        r.raise_for_status()
        self.history.append(f"מתאמן: {first}")
        self.record(r.json(), "chat")

    def next_macro(self, nxt):
        c = self.use()
        intro = c.post("/api/chat/v2/stage-intro", json={"conversation_id": self.conv_id, "target_macro_stage": nxt,
                                                          "language": "he"}, headers=sim_headers())
        intro.raise_for_status()
        answers = {q["id"]: [q["options"][0]["id"]] for q in intro.json().get("questions", []) if q.get("options")}
        r = c.post("/api/chat/v2/stage-intro-answers", json={"conversation_id": self.conv_id, "macro_stage": nxt,
                                                              "answers": answers, "language": "he"}, headers=sim_headers())
        r.raise_for_status()
        self.record(r.json(), "intro")

    def run_until(self, macro_done, A, max_turns):
        """Turns until the stage that ends `macro_done` completes; crosses earlier macro stages on the way."""
        order = ["identification", "discovery", "kamaz", "choice", "vision"]
        for _ in range(max_turns):
            if self.sc:
                done = self.sc.get("stage_id") or step_to_macro_stage(self.step)
                if done == macro_done:
                    return True
                self.next_macro(order[order.index(done) + 1])
                continue
            c = self.use()
            if self.active_tool:
                self.last_tool = self.active_tool["tool_type"]
                data = A(sim.fill_card(self.p, self.active_tool, self.history))
                self.history.append(f"מתאמן (כרטיס {self.last_tool}): {json.dumps(data, ensure_ascii=False)}")
                print(f"     🧑 [{self.last_tool}] {json.dumps(data, ensure_ascii=False)[:250]}")
                r = c.post(f"/api/tools/{self.conv_id}/submit", json={"tool_type": self.last_tool, "data": data},
                           headers=sim_headers())
                if r.status_code == 422:
                    print("     ⚠️ 422", r.text[:200])
                    self.flags.append(f"422 on {self.last_tool}: {r.text[:120]}")
                    self.active_tool = None
                    continue
                r.raise_for_status()
                self.record(r.json(), "card")
            else:
                msg = A(sim.user_reply(self.p, self.history))
                self.history.append(f"מתאמן: {msg}")
                print(f"     🧑 {msg}")
                r = c.post("/api/chat/v2/message", json={"message": msg, "conversation_id": self.conv_id,
                                                          "language": "he"}, headers=sim_headers())
                r.raise_for_status()
                self.record(r.json(), "chat")
        self.flags.append(f"did not finish {macro_done} in {max_turns} turns")
        return False


def sim_headers():
    return {"X-UX-Version": "3"}


def approve_all(partner, sid, checkpoint):
    c = partner.use()
    d = c.get(f"/api/couple/sessions/{sid}/{checkpoint}/draft")
    d.raise_for_status()
    lines = d.json()["lines"]
    r = c.post(f"/api/couple/sessions/{sid}/{checkpoint}", json={"lines": lines})
    r.raise_for_status()
    print(f"\n   ✅ {partner.p[0]} approved {checkpoint}: {len(lines)} lines")
    return lines


def print_screen(title, screen):
    print("\n" + "═" * 70 + f"\n{title}: {screen['event_title']}")
    for side in ("me", "partner"):
        s = screen[side]
        print(f"\n  ── {s['name']} ({s['gender']})")
        for line in s["lines"]:
            print(f"     {line['id']:16} {line['text']}")


def main(max_turns):
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    users = {}
    for key, p in COUPLE.items():
        u = User(clerk_id=f"couple_{key}_{time.time()}", email=f"{key}@couple.test", created_at=datetime.now(timezone.utc))
        db.add(u)
        users[key] = u
    db.commit()
    current = {"user": None}

    def _db():
        yield db
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: current["user"]
    app.dependency_overrides[require_message_quota] = lambda: current["user"]
    client = TestClient(app)
    import asyncio
    loop = asyncio.new_event_loop()
    A = loop.run_until_complete

    a, b = Partner("pursuer", client, users, current), Partner("withdrawer", client, users, current)
    checks = []

    r = a.use().post("/api/couple/sessions", json={"event_title": TITLE, "display_name": a.p[0], "gender": a.p[1]})
    r.raise_for_status()
    sid, a.conv_id, token = r.json()["session_id"], r.json()["conversation_id"], r.json()["invite_token"]
    preview = b.use().get(f"/api/couple/invites/{token}").json()
    checks.append(("invite preview = name + title only", set(preview) == {"state", "inviter_name", "inviter_gender", "event_title"}))
    r = b.use().post(f"/api/couple/invites/{token}/accept", json={"display_name": b.p[0], "gender": b.p[1]})
    r.raise_for_status()
    b.conv_id = r.json()["conversation_id"]

    for partner in (a, b):  # one at a time — never parallel (quota)
        partner.start()
        partner.run_until("discovery", A, max_turns)
        held = partner.use().post("/api/chat/v2/stage-intro", json={"conversation_id": partner.conv_id,
                                                                     "target_macro_stage": "kamaz"}, headers=sim_headers())
        checks.append((f"{partner.p[0]}: כמ\"ז held before the mirror (409)", held.status_code == 409))
        closed = partner.use().get(f"/api/couple/sessions/{sid}/mirror")
        checks.append((f"{partner.p[0]}: mirror closed before both approved", closed.status_code == 409))
        approve_all(partner, sid, "mirror")

    mirror_a = a.use().get(f"/api/couple/sessions/{sid}/mirror").json()
    mirror_b = b.use().get(f"/api/couple/sessions/{sid}/mirror").json()
    print_screen("MIRROR (as נועה sees it)", mirror_a)
    ids_a = {line["id"] for line in mirror_a["me"]["lines"]}
    ids_b = {line["id"] for line in mirror_b["me"]["lines"]}
    checks.append(("gears: both have pattern + trigger", {"pattern", "trigger"} <= ids_a and {"pattern", "trigger"} <= ids_b))
    checks.append(("mirror is symmetric", mirror_a["me"] == mirror_b["partner"]))
    # the partner's private event telling never reached this coach
    a_coach = " ".join(t[5] for t in a.trace)
    checks.append(("נועה's coach never saw איתי's words ('טובע')", "טובע" not in a_coach))

    for partner in (a, b):
        partner.sc = None
        partner.next_macro("kamaz")
        partner.run_until("vision", A, max_turns)
        approve_all(partner, sid, "commitment")
    commitment = a.use().get(f"/api/couple/sessions/{sid}/commitment").json()
    print_screen("COMMITMENT (as נועה sees it)", commitment)

    out_dir = "/tmp/couple_e2e"
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"run_{int(time.time())}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"mirror": mirror_a, "commitment": commitment,
                   "transcripts": {p.p[0]: [list(t) for t in p.trace] for p in (a, b)}}, f, ensure_ascii=False, indent=1)

    print("\n" + "=" * 70)
    for p in (a, b):
        print(f"{p.p[0]}: {len(p.trace)} turns, final step {p.step}; FLAGS ({len(p.flags)}):")
        for fl in p.flags:
            print("  ⚠️", fl)
    print("\nCHECKS:")
    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'} {name}")
    print(f"\nartifacts: {out}\ndb {sim._db}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-turns", type=int, default=45, help="per partner, per half of the process")
    main(ap.parse_args().max_turns)
