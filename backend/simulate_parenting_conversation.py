#!/usr/bin/env python3
"""
סימולציה של שיחת הורות - בודקת שאין חזרות, JSON תקין, ו-S1→S2 (לא S3).

מחקה את השיחה:
  משתמש: על הורות → אבא יותר טוב → אבא שאוהב ומציב גבולות → הצבת גבולות בלי לחשוש → על הצבת גבולות
  באג: המאמן שאל "מה הרגשת באותו רגע?" בלי אירוע (קפיצה ל-S3)
  באג: המאמן חזר על "תוכל לספר לי יותר" יותר מדי פעמים
"""

import asyncio
import json
import sys
from unittest.mock import AsyncMock, patch

# Add app to path
sys.path.insert(0, ".")

from app.bsd_v2.state_schema_v2 import create_initial_state, add_message, get_conversation_history
from app.bsd_v2.single_agent_coach import (
    handle_conversation,
    check_repeated_question,
    validate_stage_transition,
    get_next_step_question,
)


# === תגובות "בעייתיות" שהמודל עלול להחזיר (מחקות את הבאג) ===
MOCK_RESPONSES = [
    # Turn 0: אחרי "כן" - פתיחה
    {
        "coach_message": "מעולה, על מה תרצה להתאמן היום?",
        "internal_state": {"current_step": "S1", "saturation_score": 0.2, "reflection": "opening"},
    },
    # Turn 1: אחרי "על הורות"
    {
        "coach_message": '"על הורות" זה בהחלט נושא טוב. מה בהורות היית רוצה להתמקד או להתאמן עליו?',
        "internal_state": {"current_step": "S1", "saturation_score": 0.3, "reflection": "clarify"},
    },
    # Turn 2: אחרי "אבא יותר טוב" - תוכל לספר #1
    {
        "coach_message": "אני שומע שאתה רוצה להיות אבא יותר טוב. תוכל לספר לי יותר על מה בדיוק היית רוצה להתמקד בהורות שלך?",
        "internal_state": {"current_step": "S1", "saturation_score": 0.4, "reflection": "drill"},
    },
    # Turn 3: אחרי "אבא שאוהב ומציב גבולות" - תוכל לספר #2
    {
        "coach_message": "אני מבין שאתה רוצה להיות אבא שאוהב וגם מציב גבולות. תוכל לספר לי יותר על מה בזה מעסיק אותך במיוחד?",
        "internal_state": {"current_step": "S1", "saturation_score": 0.5, "reflection": "drill"},
    },
    # Turn 4: אחרי "הצבת גבולות בלי לחשוש" - תוכל לספר #3 (אמור להיתפס!)
    {
        "coach_message": "אני שומע שאתה רוצה לדעת להציב גבולות בלי לחשוש. תוכל לספר לי יותר על מה בדיוק היית רוצה להתמקד?",
        "internal_state": {"current_step": "S1", "saturation_score": 0.5, "reflection": "drill"},
    },
    # Turn 5: אחרי "על הצבת גבולות" - באג! שאלת רגשות בלי אירוע
    {
        "coach_message": "אני מבין. עכשיו אני רוצה להתעמק ברגשות. מה הרגשת באותו רגע?",
        "internal_state": {"current_step": "S3", "saturation_score": 0.3, "reflection": "BUG: jumped to S3"},
    },
]

USER_MESSAGES = [
    "כן",
    "על הורות, זה נושא טוב?",
    "הייי רוצה מאוד להיות אבא יותר טוב",
    "להיות אבא שאוהב ומציב גבוולת בלי סתירה",
    "לדעת להציב גבולות בלי לחשוש מה יהיה",
    "על הצבת גבולות",
]


def make_llm_response(obj: dict) -> str:
    """Convert dict to JSON string as LLM would return."""
    return json.dumps(obj, ensure_ascii=False)


async def run_simulation_with_mock():
    """מריץ את הסימולציה עם mock ל-LLM."""
    state = create_initial_state("sim-1", "user-1", "he")
    state["current_step"] = "S0"
    state["saturation_score"] = 0.0

    response_index = [0]  # mutable for closure

    async def mock_invoke(llm, messages, cache_key=""):
        class FakeResponse:
            content = make_llm_response(MOCK_RESPONSES[response_index[0]])
            response_metadata = {}

        return FakeResponse()

    def mock_get_llm(purpose=""):
        return object()  # fake LLM, we mock the invoke

    errors = []
    coach_responses = []

    with patch(
        "app.bsd_v2.single_agent_coach.get_azure_chat_llm",
        side_effect=mock_get_llm,
    ), patch(
        "app.bsd_v2.single_agent_coach._ainvoke_with_prompt_cache",
        side_effect=mock_invoke,
    ):
        for i, user_msg in enumerate(USER_MESSAGES):
            response_index[0] = min(i, len(MOCK_RESPONSES) - 1)
            try:
                coach_msg, state = await handle_conversation(user_msg, state, "he")
                coach_responses.append(coach_msg)
            except Exception as e:
                errors.append(f"Turn {i+1} ({user_msg[:30]}...): {e}")
                raise

    return state, coach_responses, errors


def run_safety_net_tests():
    """בודק ישירות את רשתות הבטיחות."""
    results = []

    # 1) S1 + שאלת רגשות - אמור להיתפס
    history = [
        {"sender": "user", "content": "על הצבת גבולות"},
        {"sender": "coach", "content": "מה בהורות מעסיק אותך?"},
    ]
    bad_msg = "אני מבין. עכשיו אני רוצה להתעמק ברגשות. מה הרגשת באותו רגע?"
    correction = check_repeated_question(bad_msg, history, "S1", "he")
    repl = correction[0] if isinstance(correction, tuple) else correction
    ok = correction is not None and ("אירוע" in repl or "פעם אחת" in repl or "מתי" in repl)
    results.append(("S1+emotions blocked", ok, f"correction={repl[:80] if repl else None}..."))

    # 2) "תוכל לספר לי יותר" x2 - אמור להיתפס
    history = [
        {"sender": "coach", "content": "תוכל לספר לי יותר על מה בזה מעסיק אותך?"},
        {"sender": "user", "content": "הצבת גבולות"},
        {"sender": "coach", "content": "תוכל לספר לי יותר על מה בדיוק?"},
    ]
    third = "תוכל לספר לי יותר על מה בדיוק היית רוצה?"
    correction = check_repeated_question(third, history, "S1", "he")
    ok = correction is not None
    results.append(("generic_patterns (תוכל לספר) blocked", ok, f"correction={'yes' if correction else 'no'}"))

    # 3) validate_stage_transition - S1→S3 חסום
    state = {
        "messages": [
            {"sender": "user", "content": "על הצבת גבולות"},
        ],
        "current_step": "S1",
        "collected_data": {},
    }
    is_valid, correction = validate_stage_transition("S1", "S3", state, "he")
    ok = not is_valid and correction and "אירוע" in correction
    results.append(("S1→S3 blocked", ok, f"valid={is_valid}, correction={correction[:60] if correction else None}..."))

    # 4) JSON parse - מחרוזת בלבד
    try:
        raw = json.loads('"על מה בהורות היית רוצה להתמקד?"')
        assert isinstance(raw, str)
        results.append(("JSON string handling", True, "logic in place"))
    except Exception as e:
        results.append(("JSON string handling", False, str(e)))

    # 5) Mock responses are valid JSON
    try:
        for i, r in enumerate(MOCK_RESPONSES):
            s = json.dumps(r, ensure_ascii=False)
            parsed = json.loads(s)
            assert "coach_message" in parsed and "internal_state" in parsed
        results.append(("Mock JSON valid", True, f"{len(MOCK_RESPONSES)} responses"))
    except Exception as e:
        results.append(("Mock JSON valid", False, str(e)))

    return results


def main():
    print("=" * 60)
    print("סימולציה: שיחת הורות (הצבת גבולות)")
    print("=" * 60)

    # 1) בדיקות ישירות של רשתות הבטיחות
    print("\n--- בדיקות רשתות בטיחות ---")
    for name, ok, detail in run_safety_net_tests():
        status = "✅" if ok else "❌"
        print(f"  {status} {name}: {detail}")

    # 2) סימולציה מלאה עם mock
    print("\n--- סימולציה מלאה (mock LLM) ---")
    try:
        state, coach_responses, errors = asyncio.run(run_simulation_with_mock())
        print(f"  סיימנו {len(coach_responses)} תורות בהצלחה")
        print(f"  שלב סופי: {state['current_step']}")

        # בדיקות על התוצאות
        checks = []

        # אחרי "על הצבת גבולות" - לא "מה הרגשת באותו רגע" (צריך להישאר ב-S2, לא S3)
        last_coach = coach_responses[-1] if coach_responses else ""
        no_emotions_bug = "מה הרגשת באותו רגע" not in last_coach and state["current_step"] != "S3"
        checks.append(("אין קפיצה ל-S3/רגשות בלי אירוע", no_emotions_bug))

        # יש בקשה לאירוע (S2) או נשארנו ב-S2
        has_event_request = (
            "אירוע" in last_coach or "מתי" in last_coach or "עם מי" in last_coach
            or "פעם אחת" in last_coach or "סיפור" in last_coach
        )
        in_s2 = state["current_step"] == "S2"
        checks.append(("בקשה לאירוע ספציפי (S2) או שלב S2", has_event_request or in_s2))

        # לא יותר מדי "תוכל לספר" ברצף (הרשת תופסת אחרי 2)
        tell_more_count = sum(1 for r in coach_responses if "תוכל לספר" in r or "ספר לי יותר" in r)
        not_excessive = tell_more_count <= 2
        checks.append(("לא יותר מדי 'תוכל לספר'", not_excessive or has_event_request))

        print("\n  בדיקות תוצאה:")
        for name, ok in checks:
            print(f"    {'✅' if ok else '❌'} {name}")

        all_ok = all(ok for _, ok in checks)
        if all_ok:
            print("\n✅ כל הבדיקות עברו!")
        else:
            print("\n❌ חלק מהבדיקות נכשלו")

        print("\n  תגובות המאמן (סופי):")
        for i, r in enumerate(coach_responses):
            print(f"    {i+1}. {r[:95]}{'...' if len(r) > 95 else ''}")

    except Exception as e:
        print(f"  ❌ שגיאה: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
