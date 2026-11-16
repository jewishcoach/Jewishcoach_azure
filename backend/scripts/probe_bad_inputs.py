"""
Probe: does the coach "swallow" wrong input? (user, Nov 16: "צריך לבדוק בכל השלבים שהמאמן לא בולע אינפוט שגוי")

For each stage, one wrong answer of the kind real clients give (a generalization, blaming the other, an answer to
another question, nonsense, an objection). It is sent like the app sends it: a chat reply, or a card submission
(the card's fields written into the state first, as routers/tools.py does). The coach is run once per repeat and
the result recorded:
  ADVANCED  — the step moved on (the wrong input was taken as the answer)
  HELD      — the step stayed and the coach asked / requested something
  HELD-SILENT — the step stayed but the coach didn't ask anything (judge by reading)
Read the coach text: "held" is necessary, not sufficient — the question has to address what's wrong.

Usage: python scripts/probe_bad_inputs.py [--only S7] [--repeat 2]
Real model calls (Azure); run sequentially, not in parallel with other E2E runs.
"""
import argparse
import asyncio
import copy
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./coaching.db")
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from app.bsd_v2.single_agent_coach import handle_conversation, _open_request  # noqa: E402
from app.bsd_v2.state_schema_v2 import create_initial_state  # noqa: E402
from app.bsd_v2.coaching_request import compose_coaching_request  # noqa: E402

BASE = {
    "topic": "אני מרגיש תקוע. בתחום: זוגיות",
    "event_description": "אתמול בערב — עם אשתי — היא אמרה לי מול הילדים שאני אף פעם לא עוזר בבית",
    "emotions": ["כעס", "עלבון"],
    "thought": "היא לא רואה כמה אני עושה",
    "action_actual": "שתקתי ויצאתי מהחדר",
    "emotion_desired": "שקט", "thought_desired": "היא עייפה, זה לא עליי", "action_desired": "לומר לה בשקט מה אני מרגיש",
    "gap_name": "שתיקה במקום דיבור", "gap_score": "7", "gap_booklet_moves": ["belief", "opportunity"],
    "pattern": "לשתוק ולהתרחק",
    "paradigm": "ככה זה אצלי — עדיף לשתוק מאשר לריב",
}
# what each stage already has when it starts (later fields are cleared)
ORDER = ["topic", "event_description", "emotions", "thought", "action_actual", "emotion_desired", "thought_desired",
         "action_desired", "gap_name", "gap_score", "gap_booklet_moves", "pattern", "paradigm"]
HAVE = {"S2": 1, "S3": 2, "S4": 3, "S5": 4, "S6": 5, "S7": 8, "S8": 11, "S9": 12, "S10": 13, "S11": 13,
        "S13": 13, "S14": 13, "S15": 13}
# late stages also carry the stance, the forces and the choice (set in _state)


def _coach(text, step):
    return {"sender": "coach", "content": text, "internal_state": {"current_step": step}}


_REQ = {"floor": "stance", "situation": "הערות של אשתי מול הילדים", "old": "עדיף לשתוק מאשר לריב",
        "source": ["אמת"], "nature": ["רגישות"], "new": "מותר לי לומר מה אני מרגיש", "gender": "male"}
# (id, step, kind, payload, prior coach question for chat, what's wrong)
CASES = [
    ("S2-always", "S2", "card", ("event_form", {"when": "תמיד", "with_whom": "אשתי", "what_happened": "היא תמיד מעירה לי על הכל"}), None,
     "not one moment — a generalization"),
    ("S2-alone", "S2", "card", ("event_form", {"when": "אתמול בלילה", "with_whom": "לבד", "what_happened": "ישבתי לבד וחשבתי על החיים שלי"}), None,
     "no contact with another person"),
    ("S2-nonsense", "S2", "card", ("event_form", {"when": "לא יודע", "with_whom": "מישהו", "what_happened": "סתם משהו"}), None,
     "no event at all"),
    ("S3-thoughts", "S3", "card", ("emotion_selector", {"emotions": ["שהיא לא מבינה אותי", "שאני צודק"]}), None,
     "thoughts, not emotions"),
    ("S4-emotion", "S4", "chat", "כעסתי מאוד", "ומה עבר לך בראש באותו רגע — מה האמירה הפנימית שאמרת לעצמך?",
     "an emotion, not the inner sentence"),
    ("S4-action", "S4", "chat", "יצאתי מהחדר", "ומה עבר לך בראש באותו רגע — מה האמירה הפנימית שאמרת לעצמך?",
     "an action, not the inner sentence"),
    ("S4-objection", "S4", "chat", "מה זה משנה מה חשבתי?", "ומה עבר לך בראש באותו רגע — מה האמירה הפנימית שאמרת לעצמך?",
     "an objection / question"),
    ("S5-thought", "S5", "card", ("action_field", {"action_actual": "חשבתי שהיא לא מעריכה אותי"}), None,
     "a thought, not what he did"),
    ("S6-other", "S6", "card", ("comparison_card", {"emotion_desired": "", "thought_desired": "", "action_desired": "שהיא תפסיק להעיר לי"}), None,
     "the desired is that SHE changes"),
    ("S7-blame", "S7", "card", ("gap_card", {"gap_name": "אשה מעצבנת", "gap_score": 7}), None,
     "the gap name blames the other (Nov 15)"),
    ("S7-nonsense", "S7", "card", ("gap_card", {"gap_name": "כן", "gap_score": 5}), None,
     "no gap name"),
    ("S7-irrelevant", "S7", "chat", "אני אוהב פיצה", "האם אתה מאמין שבפער הזה יש משהו טוב בשבילך?",
     "irrelevant answer to the belief question"),
    ("S8-deflect", "S8", "chat", "לא יודע מה אתה רוצה ממני", "איפה עוד אתה מזהה את אותו שילוב של רגש, מחשבה ותגובה?",
     "no example, frustration"),
    ("S9-irrelevant", "S9", "card", ("sentence_builder", {"paradigm": "השמים כחולים"}), None,
     "an irrelevant 'rule'"),
    ("S10-delegate", "S10", "chat", "תגיד אתה, אתה המאמן",
     "החוק הזה — מאיזו תפיסה על החיים, על אנשים או על עצמך הוא נולד? מה אתה יודע על העולם שגורם לו להרגיש נכון?",
     "asks the coach to answer for him"),
    ("S13-other", "S13", "card", ("declaration_card", {"renewal": "שאשתי תשתנה ותפסיק להעיר לי", "next_action": ""}), None,
     "the new choice is that SHE changes"),
    ("S5-dontknow", "S5", "card", ("action_field", {"action_actual": "לא יודע"}), None, "'I don't know' as the action"),
    ("S6-dontknow", "S6", "card", ("comparison_card", {"emotion_desired": "לא יודע", "thought_desired": "לא יודע", "action_desired": "לא יודע"}), None,
     "'I don't know' as the desired"),
    ("S7-dontknow", "S7", "card", ("gap_card", {"gap_name": "לא יודע", "gap_score": 5}), None, "'I don't know' as the gap name"),
    ("S9-dontknow", "S9", "card", ("sentence_builder", {"paradigm": "לא יודע"}), None, "'I don't know' as the paradigm"),
    ("S13-dontknow", "S13", "card", ("declaration_card", {"renewal": "אני לא יודעת מה זה יכול להיות", "next_action": "לא יודע, אותו דבר",
                                                          "feels_right": False}), None,
     "'I don't know' as the new choice (Nov 16, a client's conversation)"),
    ("S15-other", "S15", "card", ("commitment_card", dict(_REQ, result="שאשתי תפסיק להעיר לי")), None,
     "the result depends on someone else"),
    ("S15-vague", "S15", "card", ("commitment_card", dict(_REQ, result="להרגיש יותר טוב")), None,
     "a vague result"),
    ("S15-try", "S15", "card", ("commitment_card", dict(_REQ, result="אנסה להיות רגוע יותר")), None,
     "'אנסה' — no commitment"),
    ("S15-nonsense", "S15", "card", ("commitment_card", dict(_REQ, result="כן")), None,
     "no result at all"),
    ("S14-vague", "S14", "chat", "שיהיה טוב", "איך תיראה המציאות שלך בעוד שנה, כשאתה פועל מתוך הבחירה החדשה?",
     "a vague future picture"),
]

SUMMARY = {
    "event_form": lambda d: f"סיפרתי על אירוע: {d['when']} עם {d['with_whom']} — {d['what_happened']}",
    "emotion_selector": lambda d: f"הרגשות שזיהיתי: {', '.join(d['emotions'])}",
    "action_field": lambda d: f"מה שעשיתי בפועל: {d['action_actual']}",
    "comparison_card": lambda d: "הרצוי שלי: " + ". ".join(
        p for p in (f"הייתי רוצה להרגיש: {d['emotion_desired']}" if d['emotion_desired'] else "",
                    f"הייתי רוצה לחשוב: {d['thought_desired']}" if d['thought_desired'] else "",
                    f"הייתי רוצה לעשות: {d['action_desired']}" if d['action_desired'] else "") if p),
    "gap_card": lambda d: f"הפער: {d['gap_name']} (ציון {d['gap_score']}/10)",
    "sentence_builder": lambda d: f"ככה זה אצלי: {d['paradigm']}",
    "commitment_card": lambda d: f"הבקשה שלי לאימון: {compose_coaching_request(d)}",
    "declaration_card": lambda d: ". ".join(p for p in (f"העמדה החדשה שאני בוחר: {d['renewal']}",
                                                       f"מה אעשה אחרת: {d['next_action']}" if d.get("next_action") else "",
                                                       (f"מרגיש לי נכון: {'כן' if d['feels_right'] else 'עדיין לא'}"
                                                        if d.get("feels_right") is not None else "")) if p),
}


def _apply_card(cd, tool, d):
    """Mirror routers/tools.py: the card writes its fields before the coach turn."""
    if tool == "event_form":
        cd["event_description"] = " — ".join(p for p in (d["when"], f"עם {d['with_whom']}", d["what_happened"]) if p)
    elif tool == "emotion_selector":
        cd["emotions"] = d["emotions"]
    elif tool == "action_field":
        cd["action_actual"] = d["action_actual"]
    elif tool == "comparison_card":
        cd.update({k: d[k] for k in ("emotion_desired", "thought_desired", "action_desired")})
    elif tool == "gap_card":
        cd["gap_name"], cd["gap_score"] = d["gap_name"], str(d["gap_score"])
        cd["gap_booklet_moves"] = []
    elif tool == "sentence_builder":
        cd["paradigm"] = d["paradigm"]
    elif tool == "commitment_card":
        cd["commitment"] = compose_coaching_request(d)
        cd["coaching_request"] = {k: d.get(k) for k in ("floor", "situation", "old", "source", "nature", "new", "result", "gender")}
    elif tool == "declaration_card":
        cd["renewal"] = f"העמדה החדשה שבחרתי: {d['renewal']}"
        cd["renewal_belief"], cd["new_action"] = d["renewal"], d.get("next_action", "")


def _state(step):
    st = create_initial_state("probe", "probe-user", "he")
    st["current_step"], st["ux_version"] = step, 3
    keep = ORDER[:HAVE[step]]
    st["collected_data"].update({k: copy.deepcopy(v) for k, v in BASE.items() if k in keep})
    if step in ("S14", "S15"):
        st["collected_data"].update({
            "stance": {"reality_belief": "מי שמדבר — מאבד את השקט בבית", "activation_trigger": "כשמעירים לי מול אחרים",
                       "gains": ["שקט"], "losses": ["קרבה"]},
            "forces": {"source": ["אמת", "אהבה"], "nature": ["רגישות", "התמדה"]},
            "renewal": "העמדה החדשה שבחרתי: מותר לי לומר מה אני מרגיש", "renewal_belief": "מותר לי לומר מה אני מרגיש",
            "new_action": "לומר לה בשקט מה אני מרגיש"})
    return st


async def run_case(case):
    cid, step, kind, payload, prior, _why = case
    st = _state(step)
    if kind == "card":
        tool, data = payload
        _apply_card(st["collected_data"], tool, data)
        st["_tool_just_submitted"] = tool
        msg = SUMMARY[tool](data)
    else:
        st["messages"] = [_coach(prior, step)]
        msg = payload
    t0 = time.time()
    coach, after = await handle_conversation(msg, st, "he")
    moved = after.get("current_step") != step
    verdict = "ADVANCED" if moved else ("HELD" if _open_request(coach) else "HELD-SILENT")
    return {"id": cid, "step": step, "to": after.get("current_step"), "verdict": verdict,
            "secs": round(time.time() - t0, 1), "coach": coach}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--repeat", type=int, default=2)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    results = []
    for case in CASES:
        if a.only and not case[0].startswith(a.only):
            continue
        for r in range(a.repeat):
            res = await run_case(case)
            res["why"] = case[5]
            results.append(res)
            print(f"{res['id']:<15} {res['verdict']:<11} {res['step']}→{res['to']:<4} | {res['coach'][:170]}", flush=True)
    if a.out:
        with open(a.out, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=1)
    bad = [r for r in results if r["verdict"] != "HELD"]
    print(f"\n{len(results)} runs, {len(results) - len(bad)} HELD, {len(bad)} ADVANCED/SILENT")


if __name__ == "__main__":
    asyncio.run(main())
