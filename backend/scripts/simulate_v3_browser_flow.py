"""
Browser E2E of the full V3 flow: real frontend (vite dev) + real backend (uvicorn, temp SQLite),
driven by Playwright with the same LLM personas as simulate_v3_e2e_flow.py. Run from backend/:
    .venv/bin/python -u scripts/simulate_v3_browser_flow.py --persona career [--headed]

Login uses the dev-only E2E bypass (localStorage e2e_demo=true → demo token; backend demo mode
on localhost). Besides completing the flow, it checks frontend bugs:
  - every coach/user message returned by the API is actually rendered (content dedup)
  - a 422 (gibberish) shows the user some feedback
  - reloading mid-flow restores messages and the active card (resume)
  - JS console errors / page errors
Screenshots + log go to /tmp/v3_browser/<persona>/.
"""
import os, sys, json, re, time, argparse, asyncio, subprocess, signal, threading, urllib.request

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
import simulate_v3_e2e_flow as sim  # personas, LLM sim-user, temp DB (sim._db)
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

FRONTEND_DIR = os.path.join(os.path.dirname(os.getcwd()), "frontend")
BACKEND_PORT, FRONTEND_PORT = 8000, 5173
APP_URL = f"http://localhost:{FRONTEND_PORT}/?v3"
API_PATHS = ("/chat/v2/message", "/tools/", "/chat/v2/stage-intro-answers")

CARD_TITLES = {
    "האירוע": "event_form", "מה הרגשת באותו רגע?": "emotion_selector", "מה עשית?": "action_field",
    "תמונת המצוי שלך": "matzui_summary", "באותו רגע בדיוק — מה היית רוצה?": "comparison_card",
    "הפער": "gap_card", "מה החוק הפנימי שלך?": "sentence_builder",
    "מה אני מרוויח ומה אני מפסיד?": "balance_scale", "כרטיס כמ\"ז — מקור וטבע": "trait_card_builder",
    "הבזקי מקור וטבע": "kamaz_discovery",
    "הבחירה החדשה שלך": "declaration_card", "המחויבות שלך": "commitment_card", "הבקשה שלך לאימון": "commitment_card",
}


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def wait_http(url, timeout=90):
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(url, timeout=3)
            return True
        except Exception as e:
            if getattr(e, "code", None):  # any HTTP status = server is up
                return True
            time.sleep(1)
    return False


SAFETY_WORDS = ("ער\"ן", "1201", "סה\"ר", "101", "1221", "עזרה מקצועית", "גורם מקצועי", "קו חם", "לבד עם זה", "בטוחה")


def start_servers(out_dir, gender):
    sim.Base.metadata.create_all(bind=sim.engine)
    # Pre-create the demo user (backend demo mode reuses it) so the coach addresses the persona's gender
    db = sim.sessionmaker(bind=sim.engine)()
    db.add(sim.User(clerk_id="demo_user_tunnel", email="demo@tunnel.test", display_name="Demo User",
                    gender=gender, created_at=sim.datetime.now(sim.timezone.utc)))
    db.commit(); db.close()
    env = dict(os.environ, DATABASE_URL=f"sqlite:///{sim._db}", ALLOW_DEMO_MODE="true", ALLOW_DEMO_LOCALHOST="true")
    be = subprocess.Popen([".venv/bin/uvicorn", "app.main:app", "--port", str(BACKEND_PORT)],
                          env=env, stdout=open(f"{out_dir}/backend.log", "w"), stderr=subprocess.STDOUT,
                          start_new_session=True)
    fe = subprocess.Popen(["npm", "run", "dev", "--", "--port", str(FRONTEND_PORT), "--strictPort"],
                          cwd=FRONTEND_DIR, stdout=open(f"{out_dir}/frontend.log", "w"), stderr=subprocess.STDOUT,
                          start_new_session=True)
    if not wait_http(f"http://localhost:{BACKEND_PORT}/docs") or not wait_http(f"http://localhost:{FRONTEND_PORT}/"):
        stop_servers(be, fe)
        sys.exit(f"servers did not start — see {out_dir}/backend.log / frontend.log")
    return be, fe


def stop_servers(*procs):
    for p in procs:
        try:
            os.killpg(p.pid, signal.SIGTERM)
        except Exception:
            pass


class Driver:
    def __init__(self, page, persona_key, out_dir):
        self.page, self.out = page, out_dir
        self.p = sim.PERSONAS[persona_key]
        self.safety = persona_key == "crisis"
        self.safety_said = False
        self.history, self.flags, self.api = [], [], []
        self.step, self.tool, self.turn = "S0", None, 0
        # Playwright's sync API owns this thread's event loop — run the sim-user LLM on its own loop/thread
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        page.on("response", self._on_response)
        page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text
                and self.flag(f"console error: {m.text[:160]}"))
        page.on("pageerror", lambda e: self.flag(f"page error: {str(e)[:160]}"))

    def A(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()

    def flag(self, msg):
        self.flags.append(f"[{self.turn:02d}|{self.step}] {msg}")
        print("     ⚠️", msg)

    def shot(self, name):
        self.page.screenshot(path=f"{self.out}/{self.turn:02d}_{name}.png", full_page=True)

    def _on_response(self, resp):
        if resp.status >= 400 and "clerk" not in resp.url and not any(p in resp.url for p in API_PATHS):
            self.flag(f"HTTP {resp.status} {resp.request.method} {resp.url[:120]}")
        if resp.request.method != "POST" or not any(p in resp.url for p in API_PATHS):
            return
        try:
            body = resp.json()
        except Exception:
            body = {}
        self.api.append((resp.status, resp.url, body))

    # ---------- state detection ----------
    def visible(self, locator, timeout=0):
        if not timeout:
            return locator.first.is_visible()
        try:
            locator.first.wait_for(state="visible", timeout=timeout)
            return True
        except PWTimeout:
            return False

    def active_card(self):
        return self.page.locator('div[dir="rtl"][class*="border-t-2"]').last

    def detect(self):
        pg = self.page
        if (self.visible(pg.get_by_role("button", name=re.compile(r"^אני מרגיש(?:ה)? תקוע(?:ה)?$")))
                or self.visible(pg.get_by_placeholder("למשל: יש לי קונפליקט", exact=False))):
            return "onboarding"
        if self.visible(pg.get_by_role("button", name="להמשך לסיכום השלב")):
            return "summary_button"
        if self.visible(pg.get_by_text("כרטיס התובנה שלך")):
            return "stage_complete"
        if self.visible(pg.get_by_role("button", name=re.compile(r"^אני מוכנ(?:ה)? להתחיל$"))):
            return "stage_intro"
        if self.visible(pg.get_by_role("button", name="נמשיך מאיפה שעצרנו")):
            return "welcome_back"
        card = self.active_card()
        if self.visible(card):
            title = norm(card.locator("h3").first.inner_text())
            return f"card:{CARD_TITLES.get(title, title)}"
        box = pg.get_by_placeholder("כתוב את תשובתך כאן...")
        if self.visible(box) and box.is_enabled():
            return "chat"
        return "busy"

    # ---------- API bookkeeping + render checks ----------
    def wait_api(self, n_before, timeout=180):
        end = time.time() + timeout
        while time.time() < end and len(self.api) <= n_before:
            self.page.wait_for_timeout(300)
        if len(self.api) <= n_before:
            self.flag("no API response within timeout")
            return None
        status, url, body = self.api[-1]
        if status >= 400:
            return status, body
        coach = body.get("coach_message") or body.get("opening_message") or ""
        new_step = body.get("current_step") or self.step
        tool = body.get("tool_call")
        print(f"\n[{self.turn:02d}] {self.step}→{new_step}" + (f"  🃏 {tool['tool_type']}" if tool else "") + ("  🏁" if body.get("stage_complete") else ""))
        print(f"     🤖 {coach[:300]}")
        self.history.append(f"מאמן: {coach}")
        self.step, self.tool = new_step, tool
        if coach:
            self.expect_rendered(coach, "coach message")
        if "יש לך מחשבות לפגוע בעצמך" in coach and not self.safety:
            self.flag("SAFETY FALSE ALARM: check-in shown to a non-risk persona")
        return status, body

    def expect_rendered(self, text, what, timeout=20000):
        # Compare on a distinctive snippet (typing animations / markdown can alter edges)
        words = norm(re.sub(r"[*_`#>]", "", text)).split(" ")
        snippet = " ".join(words[: min(6, len(words))])
        try:
            self.page.get_by_text(snippet, exact=False).first.wait_for(state="visible", timeout=timeout)
        except PWTimeout:
            self.flag(f"{what} NOT rendered: '{snippet}'")
            self.shot("not_rendered")

    # ---------- actions ----------
    def do_onboarding(self):
        pg = self.page
        name, gender, topic, emo, event, bg = self.p
        if getattr(self, "mobile", False):  # the opening questions on the phone (long options overflowed fixed boxes)
            pg.get_by_role("button", name=re.compile(r"שהחיים שלי יכולים להיות אחרת")).scroll_into_view_if_needed()
            self.page.screenshot(path=f"{self.out}/{self.turn:02d}_onboarding.png")
        pg.get_by_role("button", name=re.compile(r"^אני מרגיש(?:ה)? תקוע(?:ה)?$")).click()  # a chip advances the step
        domain = {"זוגיות": "זוגיות", "הורות": "משפחה", "קריירה": "עבודה", "עבודה": "עבודה", "משפחה": "משפחה",
                  "הגשמה אישית": "הגשמה אישית", "בריאות": "בריאות", "כסף": "כסף"}.get(topic, "אחר")
        pg.get_by_role("button", name=domain, exact=True).click()
        pg.get_by_placeholder("למשל: יש לי קונפליקט", exact=False).fill(bg)
        n = len(self.api)
        pg.get_by_role("button", name="בוא נתחיל").click()
        self.history.append(f"מתאמן: {bg}")
        self.wait_api(n)

    def do_chat(self, text=None):
        msg = text or self.A(sim.user_reply(self.p, self.history))
        self.chat_turns = getattr(self, "chat_turns", 0) + 1
        if self.safety and not self.safety_said and self.chat_turns == 1 and not text:
            msg = f"{msg} {sim.SAFETY_TRIGGER}"
        print(f"     🧑 {msg}")
        box = self.page.get_by_placeholder("כתוב את תשובתך כאן...")
        box.fill(msg)
        n = len(self.api)
        box.press("Enter")
        self.expect_rendered(msg, "user message")
        res = self.wait_api(n)
        if res and res[0] < 400 and not text:
            self.history.insert(len(self.history) - 1, f"מתאמן: {msg}")
        if self.safety and not self.safety_said and ("לא אהיה פה" in msg or "לא לחיות" in msg):
            self.safety_said = True
            coach = (res[1].get("coach_message") or "") if res else ""
            hit = [w for w in SAFETY_WORDS if w in coach]
            print(f"   🛟 safety trigger said → coach safety words: {hit}")
            self.page.wait_for_timeout(800)
            self.shot("safety_message")
            if not hit:
                self.flag(f"SAFETY: risk statement got no safety response: '{coach[:200]}'")
                self.shot("safety_miss")
        return res

    def do_card(self, tool_type, override=None):
        card, pg = self.active_card(), self.page
        tool = self.tool if (self.tool or {}).get("tool_type") == tool_type else {"tool_type": tool_type, "data": {}}
        try:
            data = {} if tool_type == "matzui_summary" else self.A(sim.fill_card(self.p, tool, self.history))
        except ValueError:  # sim-user blocked by Azure's content filter → non-JSON fallback; use defaults below
            print("     ⚠️ sim-user card fill failed — using defaults")
            data = {}
        data.update(override or {})
        print(f"     🧑 [{tool_type}] {json.dumps(data, ensure_ascii=False)[:220]}")
        self.history.append(f"מתאמן (כרטיס {tool_type}): {json.dumps(data, ensure_ascii=False)}")
        btn = lambda name: card.get_by_role("button", name=name, exact=True)
        ph = lambda text: card.get_by_placeholder(text, exact=False)
        s = lambda v: str(v or "").strip() or "לא בטוח"

        def tags(placeholder, values, minimum):
            inp = ph(placeholder)
            vals = [s(v) for v in values if s(v)]
            vals += [f"דבר {i}" for i in range(1, minimum + 1)]  # pad if LLM gave too few/duplicates
            for v in vals[: max(minimum, len(values))]:
                inp.fill(v)
                inp.press("Enter")

        if tool_type == "event_form":
            ph("למשל: אתמול בערב").fill(s(data.get("when")))
            ph("למשל: בן/בת הזוג").fill(s(data.get("with_whom")))
            what = s(data.get("what_happened"))
            ph("מה קרה שם?").fill(what if len(what) >= 20 else what + " — ככה זה היה באותו רגע.")
            submit = btn("המשך")
        elif tool_type == "emotion_selector":
            chosen = 0
            for e in data.get("emotions") or []:
                chip = card.get_by_role("button", name=s(e), exact=True)
                if self.visible(chip):
                    chip.click(); chosen += 1
            for e in ["כעס", "תסכול", "עלבון"]:
                if chosen >= 2:
                    break
                card.get_by_role("button", name=e, exact=True).click(); chosen += 1
            submit = btn("המשך")
        elif tool_type == "action_field":
            card.locator("textarea").first.fill(s(data.get("action_actual") or next(iter(data.values()), "")))
            submit = btn("המשך")
        elif tool_type == "matzui_summary":
            submit = btn("זה מדויק, נמשיך")
        elif tool_type == "comparison_card":
            ph("איזה רגש?").fill(s(data.get("emotion_desired")))
            ph("איזו אמירה פנימית?").fill(s(data.get("thought_desired")))
            ph("איזו פעולה?").fill(s(data.get("action_desired")))
            submit = btn("המשך")
        elif tool_type == "gap_card":
            ph("למשל: ביטול עצמי").fill(s(data.get("gap_name")))
            score = max(1, min(10, int(data.get("gap_score") or 7)))
            btn(str(score)).click()
            submit = btn("המשך")
        elif tool_type == "sentence_builder":
            paradigm = re.sub(r"^\s*ככה זה אצלי\s*[—–-]?\s*", "", s(data.get("paradigm")))
            ph("אם... אז עדיף").fill(paradigm or "עדיף לשתוק")
            submit = btn("הבנתי את החוק שלי")
        elif tool_type == "balance_scale":
            tags("אני מרגיש", data.get("gains") or [], 2)
            tags("אני מפסיד", data.get("losses") or [], 2)
            submit = btn("סיימתי את המאזן")
        elif tool_type == "kamaz_discovery":
            answers = {a.get("id"): s(a.get("text")) for a in data.get("answers") or [] if isinstance(a, dict)}
            qs = (tool.get("data") or {}).get("questions") or []
            for side, nxt in (("source", "המשך לטבע"), ("nature", None)):
                for i, q in enumerate([q for q in qs if q.get("side") == side]):
                    card.locator("textarea").nth(i).fill(answers.get(q.get("id")) or "לא בטוח")
                if side == "source":  # the hidden example chips, opened once — for the screenshot
                    card.get_by_role("button", name="נתקעת?").first.click()
                self.shot(f"kamaz_{side}")
                if nxt:
                    btn(nxt).click()
            submit = btn("סיימתי")
        elif tool_type == "trait_card_builder":
            bank = (tool.get("data") or {}).get("bank") or {}
            label = {t["short"]: t["label"] for side in ("source", "nature") for t in bank.get(side) or []}
            for side, key in (("source", "source_forces"), ("nature", "nature_forces")):
                picked = 0
                options = [t["short"] for t in bank.get(side) or []]
                for v in [x for x in (data.get(key) or []) if x in options] + options:
                    if picked >= 6:
                        break
                    chip = card.get_by_role("button", name=f"+ {label.get(v, v)}", exact=True)
                    if self.visible(chip) and chip.is_enabled():
                        chip.click(); picked += 1
            self.shot("kamaz_card")
            btn("המשך").click()
            for side, key in (("source", "selected_source"), ("nature", "selected_nature")):
                for v in data.get(key) or []:
                    chip = card.get_by_role("button", name=label.get(v, v), exact=True)
                    if self.visible(chip):
                        chip.click()
            self.shot("kamaz_event")
            submit = btn("זה הכרטיס שלי")
        elif tool_type == "declaration_card":
            ph("תפיסה חדשה, במשפט קצר").fill(s(data.get("renewal")))
            ph("פעולה קונקרטית").fill(s(data.get("next_action")))
            btn("כן, זה אני!").click()
            submit = btn("זו הבחירה שלי")
        elif tool_type == "commitment_card":  # בקשה לאימון
            areas = card.locator("textarea")  # situation, old, new, result (the floor is fixed: stance)
            areas.nth(0).fill(s(data.get("situation")))
            for i, key in ((1, "old"), (2, "new")):
                if not areas.nth(i).input_value().strip():
                    areas.nth(i).fill(s(data.get(key)))
            areas.nth(3).fill(s(data.get("result")))
            tool_data = (tool or {}).get("data") or {}
            for key, sel in (("forces_source", "selected_source"), ("forces_nature", "selected_nature")):
                if tool_data.get(sel):
                    continue  # preselected from his S12 choice — a click would turn it off
                options = tool_data.get(key) or []
                wanted = [o for o in (data.get("source" if key == "forces_source" else "nature") or []) if o in options]
                for o in (wanted or options[:1]):
                    btn(o).first.click()
            submit = btn("זו הבקשה שלי")
        else:
            self.flag(f"unknown card '{tool_type}'")
            submit = card.get_by_role("button").last

        try:
            submit.wait_for(state="visible", timeout=5000)
            if not submit.is_enabled():
                self.flag(f"submit disabled on {tool_type} after filling"); self.shot(f"disabled_{tool_type}")
                return False
        except PWTimeout:
            self.flag(f"submit button not found on {tool_type}"); self.shot(f"nosubmit_{tool_type}")
            return False
        if getattr(self, "mobile", False):
            card.scroll_into_view_if_needed()
            self.shot(f"card_{tool_type}")  # every filled card on the phone, before it is sent
        n = len(self.api)
        submit.click()
        res = self.wait_api(n)
        if res and res[0] >= 400 and not override:
            self.flag(f"card {tool_type} submit → HTTP {res[0]}: {json.dumps(res[1], ensure_ascii=False)[:150]}")
        return res

    def click_and_wait(self, name, expect_api):
        n = len(self.api)
        self.page.get_by_role("button", name=name).first.click()
        if expect_api:
            self.wait_api(n)
        else:
            self.page.wait_for_timeout(1500)

    # ---------- bug probes ----------
    def probe_gibberish(self):
        """Submit gap_card with a gibberish gap name → backend 422. Does the user learn why, and keep their input?"""
        print("\n   🧪 probe: gibberish in gap_card")
        res = self.do_card("gap_card", override={"gap_name": "ההההה"})
        if not res or res[0] != 422:
            return self.flag(f"gibberish probe: expected 422, got {res and res[0]}")
        self.history.pop()  # don't feed the probe to the sim user
        self.page.wait_for_timeout(1500)
        body = norm(self.page.locator("body").inner_text())
        server_msg = ((res[1].get("detail") or {}) if isinstance(res[1].get("detail"), dict) else {}).get("message", "")
        print(f"     → 422; server says: '{server_msg}'")
        if server_msg and server_msg not in body:
            generic = "משהו השתבש" in body
            self.flag("gibberish 422: server message not shown" + (" — user sees generic 'משהו השתבש'" if generic else " — no feedback"))
            self.shot("gibberish_feedback")
        if not self.visible(self.active_card(), 3000):
            self.flag("gibberish 422: card not restored for retry")
        else:
            others = [norm(self.active_card().locator("input").nth(i).input_value()) for i in range(self.active_card().locator("input").count())]
            if not any(others):
                self.flag("gibberish 422: restored card is EMPTY — user's input lost")

    def probe_resume(self):
        print("\n   🧪 probe: reload mid-flow")
        pg = self.page
        state_before = self.detect()
        body_before = norm(pg.locator("body").inner_text())
        msgs_before = [m for m in (" ".join(norm(h[6:]).split(" ")[:5]) for h in self.history if h.startswith("מאמן: ") and h[6:].strip())
                       if m and m in body_before]
        self.shot("before_reload")
        pg.reload()
        pg.wait_for_timeout(4000)
        if self.detect() == "welcome_back":
            pg.get_by_role("button", name="נמשיך מאיפה שעצרנו").click()
            pg.wait_for_timeout(2500)
        state_after = self.detect()
        body = norm(pg.locator("body").inner_text())
        missing = [m for m in msgs_before if m not in body]
        print(f"     → state {state_before} → {state_after}; coach messages missing after reload: {len(missing)}/{len(msgs_before)}")
        if state_after != state_before:
            self.flag(f"resume: state changed {state_before} → {state_after}")
        if missing:
            self.flag(f"resume: {len(missing)}/{len(msgs_before)} coach messages gone after reload (e.g. '{missing[0]}')")
        self.shot("after_reload")

    # ---------- main loop ----------
    def run(self, max_turns, probe_resume_at, probe_gibberish_at):
        pg = self.page
        pg.goto(APP_URL)
        pg.evaluate("() => { localStorage.setItem('e2e_demo', 'true'); localStorage.setItem('ux_v3', 'true'); }")
        pg.reload()
        probed = set()
        idle = 0
        while self.turn < max_turns:
            state = self.detect()
            if state == "busy":
                idle += 1
                if idle > 120:
                    self.flag("UI stuck in busy state for 60s"); self.shot("stuck"); break
                pg.wait_for_timeout(500); continue
            idle = 0
            self.turn += 1
            if state == "card:gap_card" and probe_gibberish_at and "gib" not in probed:
                probed.add("gib"); self.probe_gibberish(); continue
            if self.step == probe_resume_at and "resume" not in probed and state.startswith("card:"):
                probed.add("resume"); self.probe_resume(); continue
            if state == "onboarding":
                self.do_onboarding()
            elif state == "chat":
                self.do_chat()
            elif state.startswith("card:"):
                if not self.do_card(state[5:]):
                    break
            elif state == "stage_complete":
                self.shot("stage_complete")
                if self.step == "S15":
                    print("\n✅ FLOW COMPLETE"); break
                pg.wait_for_timeout(int(float(os.getenv("SIM_READ_SECONDS", "0")) * 1000))  # a human reads the summary
                t0 = time.time()
                self.click_and_wait("המשך לצעד הבא", expect_api=False)
                if self.visible(pg.get_by_role("button", name=re.compile(r"^אני מוכנ(?:ה)? להתחיל$")), 60000):
                    print(f"   ⏱ stage intro ready {time.time() - t0:.1f}s after 'המשך לצעד הבא'")
            elif state == "summary_button":
                self.click_and_wait("להמשך לסיכום השלב", expect_api=False)
            elif state == "stage_intro":
                if getattr(self, "mobile", False):
                    self.shot("stage_intro")
                self.click_and_wait(re.compile(r"^אני מוכנ(?:ה)? להתחיל$"), expect_api=True)
            elif state == "welcome_back":
                self.click_and_wait("נמשיך מאיפה שעצרנו", expect_api=False)
        if self.safety and not self.safety_said:
            self.flag("SAFETY: persona never said the risk statement — probe did not run")
        self.shot("final")
        print("\n" + "=" * 70)
        print(f"{self.turn} UI turns, final step {self.step}")
        print(f"FLAGS ({len(self.flags)}):")
        for f in self.flags:
            print("  ⚠️", f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", default="career")
    ap.add_argument("--max-turns", type=int, default=60)
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--probe-resume-at", default="S9", help="reload the page when the card of this step is shown")
    ap.add_argument("--probe-gibberish-at", default="gap_card", help="'' to disable")
    a = ap.parse_args()
    sim.STYLE = a.persona if a.persona in sim.STYLES else None
    out = f"/tmp/v3_browser/{a.persona}"
    os.makedirs(out, exist_ok=True)
    be, fe = start_servers(out, sim.PERSONAS[a.persona][1])
    mobile = a.persona in sim.MOBILE_PERSONAS
    print(f"persona {a.persona} ({'mobile 390x844' if mobile else 'desktop'})")
    print(f"db {sim._db}")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=not a.headed)
            if mobile:
                device = {k: v for k, v in pw.devices["iPhone 13"].items() if k != "default_browser_type"}
                page = browser.new_page(**device, locale="he-IL")
            else:
                page = browser.new_page(viewport={"width": 1280, "height": 900}, locale="he-IL")
            page.set_default_timeout(15000)
            driver = Driver(page, a.persona, out)
            driver.mobile = mobile
            driver.run(a.max_turns, a.probe_resume_at, a.probe_gibberish_at)
            browser.close()
    finally:
        stop_servers(be, fe)


if __name__ == "__main__":
    main()
