"""
Coaching Behavior Regression Tests — catches the exact bugs we found in QA.

Uses real LLM calls through handle_conversation() to verify coach behavior.
Each test sends a specific problematic input and checks the coach doesn't
repeat past mistakes (skipping stages, parroting, inventing interpretations).

Usage:
    cd backend
    .venv/bin/python scripts/test_coaching_regressions.py
    .venv/bin/python scripts/test_coaching_regressions.py --test s2_vague
    .venv/bin/python scripts/test_coaching_regressions.py --verbose
"""

import asyncio
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./coaching.db")

from dotenv import load_dotenv
load_dotenv()

from app.bsd_v2.single_agent_coach import handle_conversation
from app.bsd_v2.state_schema_v2 import create_initial_state


def _make_state(step: str, collected_data: dict = None, ux_version: int = 3) -> dict:
    state = create_initial_state("reg-test", "reg-user", "he")
    state["current_step"] = step
    state["ux_version"] = ux_version
    if collected_data:
        state["collected_data"].update(collected_data)
    return state


def _has_question(text: str) -> bool:
    return "?" in text


def _contains_any(text: str, phrases: list[str]) -> bool:
    lower = text.lower()
    return any(p in lower for p in phrases)


# ═══════════════════════════════════════════════════════════════════════════════
# REGRESSION TESTS — each one is a past bug
# ═══════════════════════════════════════════════════════════════════════════════

TESTS = {}

def regression(name: str, description: str):
    def decorator(func):
        TESTS[name] = {"fn": func, "desc": description}
        return func
    return decorator


# ── S2: vague event should not pass ──────────────────────────────────────────

@regression("s2_vague_event", "S2: 'מריבה' without detail should trigger follow-up, not advance to S3")
async def test_s2_vague_event():
    state = _make_state("S2", {"event_description": "מריבה", "topic": "זוגיות"})
    coach, state = await handle_conversation("מריבה עם אשתי", state, "he")

    issues = []
    if state.get("current_step") == "S3":
        issues.append("SKIPPED: Advanced to S3 without event detail")
    if not _has_question(coach):
        issues.append("NO_FOLLOWUP: Didn't ask for detail about the event")
    if "עכשיו נזהה" in coach and state.get("current_step") == "S3":
        issues.append("PREMATURE_TRANSITION: Moved to emotions without detail")
    return coach, issues


# ── S2→S3: should not ask "מה הרגשת?" ───────────────────────────────────────

@regression("s2_to_s3_no_question", "S2→S3: When event is complete, should NOT ask 'מה הרגשת?' — card appears")
async def test_s2_to_s3_no_question():
    state = _make_state("S2", {
        "event_description": "אתמול בערב אשתי רצתה שאכין אוכל, אמרתי שאין לי כוח, היא התפרצה שאני לא עושה כלום בבית, ויצאתי מהבית",
        "topic": "זוגיות"
    })
    coach, state = await handle_conversation("היא צעקה שאני לא עושה כלום ויצאתי", state, "he")

    issues = []
    if _contains_any(coach, ["מה הרגשת", "איזה רגשות", "מה עלה בך"]):
        if _has_question(coach):
            issues.append("ASKED_EMOTION: Asked 'מה הרגשת?' instead of warm statement + card")
    return coach, issues


# ── S3: anti-interpretation ──────────────────────────────────────────────────

@regression("s3_no_interpretation", "S3: Should NOT invent reasons for emotions ('הכעס נובע מ...')")
async def test_s3_no_interpretation():
    state = _make_state("S3", {
        "emotions": ["כעס", "תסכול", "עלבון"],
        "event_description": "מריבה עם אשתי על סידור הבית"
    })
    coach, state = await handle_conversation("", state, "he")

    issues = []
    interpretation_patterns = ["נובע מ", "בגלל", "כי זה נוגע", "מובן כי", "קשור ל"]
    for pat in interpretation_patterns:
        if pat in coach:
            issues.append(f"INTERPRETATION: Coach added '{pat}' — inventing reasons for emotions")
            break
    return coach, issues


# ── S3: "מה זה משנה?" should not skip ───────────────────────────────────────

@regression("s3_resistance_no_skip", "S3: 'מה זה משנה?' should stay in S3, not skip to S4")
async def test_s3_resistance_no_skip():
    state = _make_state("S3", {
        "emotions": ["כעס", "תסכול"],
        "event_description": "מריבה עם אשתי"
    })
    # First turn: coach does recognition
    coach1, state = await handle_conversation("", state, "he")
    # Second turn: user pushes back
    coach2, state = await handle_conversation("מה זה משנה?", state, "he")

    issues = []
    if _contains_any(coach2, ["אמירה פנימית", "מה עבר לך בראש", "מה חשבת"]):
        issues.append("SKIPPED_TO_S4: Jumped to thought question after resistance")
    return coach2, issues


# ── S4→S5: should not combine stages ────────────────────────────────────────

@regression("s4_no_combined_question", "S4: Should confirm thought, NOT ask S5 question in same turn")
async def test_s4_no_combined_question():
    state = _make_state("S4", {
        "emotions": ["כעס", "עלבון"],
        "event_description": "מריבה עם אשתי",
        "topic": "זוגיות"
    })
    coach, state = await handle_conversation("אני בעל גרוע", state, "he")

    issues = []
    if _contains_any(coach, ["מה עשית", "בפועל", "צופה מהצד"]):
        if _has_question(coach):
            issues.append("COMBINED_STAGES: Asked S5 question (action) in S4 response")
    if "אם כן" in coach:
        issues.append("CONDITIONAL: Used 'אם כן' — combining confirmation with next question")
    return coach, issues


# ── S6: nonsense desired should trigger clarification ────────────────────────

@regression("s6_nonsense_desired", "S6: Nonsensical desired (depression as desired emotion) should trigger clarification")
async def test_s6_nonsense_desired():
    state = _make_state("S6", {
        "emotions": ["כעס"],
        "thought": "אני בעל גרוע",
        "action_actual": "הרבצתי לקיר",
        "emotion_desired": "דיכאון",
        "thought_desired": "אוף",
        "action_desired": "הכה",
    })
    coach, state = await handle_conversation("", state, "he")

    issues = []
    if "דיכאון" in coach and "אוף" in coach and "הכה" in coach and not _has_question(coach):
        issues.append("PARROT: Repeated nonsense desired without any clarification")
    if not _has_question(coach) and state.get("current_step") == "S7":
        issues.append("SKIPPED: Advanced to S7 without validating nonsensical desired")
    return coach, issues


# ── S7: "מה הכוונה?" should not skip to S8 ─────────────────────────────────

@regression("s7_clarification_no_skip", "S7: 'מה הכוונה?' should stay in S7, not jump to S8 pattern question")
async def test_s7_clarification_no_skip():
    state = _make_state("S7", {
        "gap_name": "ביטול עצמי",
        "gap_score": "7",
        "emotions": ["כעס", "עלבון"],
        "thought": "אני בעל גרוע",
        "action_actual": "יצאתי מהבית",
    })
    # First turn: coach asks belief question
    coach1, state = await handle_conversation("", state, "he")
    # Second turn: user asks for clarification
    coach2, state = await handle_conversation("מה הכוונה?", state, "he")

    issues = []
    if _contains_any(coach2, ["דפוס", "מזהה את עצמך", "עוד מקומות", "חוזר על עצמ"]):
        issues.append("SKIPPED_TO_S8: Jumped to pattern question after clarification request")
    if state.get("current_step") == "S8":
        issues.append("ADVANCED_TO_S8: Backend advanced to S8 without belief+opportunity")
    return coach2, issues


# ── S5: interpretive action should be grounded ───────────────────────────────

@regression("s5_interpretive_action", "S5: 'ויתרתי' should trigger grounding question, not be accepted as-is")
async def test_s5_interpretive_action():
    state = _make_state("S5", {
        "emotions": ["כעס", "עלבון"],
        "thought": "אני בעל גרוע",
        "action_actual": "ויתרתי",
        "event_description": "מריבה עם אשתי",
    })
    coach, state = await handle_conversation("", state, "he")

    issues = []
    if "ויתרתי" in coach and not _has_question(coach):
        issues.append("ACCEPTED_INTERPRETIVE: Accepted 'ויתרתי' without grounding question")
    if not _contains_any(coach, ["צופה מהצד", "רואה אותך", "בפועל", "פיזית", "מה עשית ממש"]):
        if not _has_question(coach):
            issues.append("NO_GROUNDING: Didn't ask grounding question for interpretive action")
    return coach, issues


# ── S5→S6: warm statement, no question ───────────────────────────────────────

@regression("s5_to_s6_no_question", "S5→S6: Observable action should get warm summary, NOT 'מה היית רוצה?'")
async def test_s5_to_s6_no_question():
    state = _make_state("S5", {
        "emotions": ["כעס", "עלבון"],
        "thought": "אני בעל גרוע",
        "action_actual": "קמתי וטרקתי את הדלת ויצאתי מהבית",
        "event_description": "מריבה עם אשתי",
    })
    coach, state = await handle_conversation("", state, "he")

    issues = []
    if _contains_any(coach, ["מה היית רוצה", "איך היית רוצה"]) and _has_question(coach):
        issues.append("ASKED_DESIRED: Asked desired question instead of warm statement + card")
    return coach, issues


# ── S8: pattern confirmed → S9 warm statement ───────────────────────────────

@regression("s8_to_s9_no_question", "S8→S9: After pattern confirmed, warm statement — NOT 'מהי הפרדיגמה?'")
async def test_s8_to_s9_no_question():
    state = _make_state("S8", {
        "emotions": ["כעס", "עלבון"],
        "thought": "אני בעל גרוע",
        "action_actual": "יצאתי מהבית",
        "gap_name": "ביטול עצמי",
        "gap_score": "8",
        "pattern": "כל פעם שמישהו מעיר לי — כעס, 'אני גרוע', ובריחה",
        "event_description": "מריבה עם אשתי",
    })
    coach, state = await handle_conversation("כן, בדיוק ככה — גם בעבודה כשהבוס מעיר לי, וגם מול ההורים", state, "he")

    issues = []
    if _contains_any(coach, ["מהי הפרדיגמה", "ככה זה אצלי", "חוק פנימי", "טייס אוטומטי"]):
        if _has_question(coach):
            issues.append("ASKED_PARADIGM: Asked paradigm question instead of warm statement + card")
    return coach, issues


# ── S9: pattern written in paradigm field → should correct ───────────────────

@regression("s9_pattern_in_paradigm", "S9: User writes pattern in paradigm field — coach should correct to paradigm level")
async def test_s9_pattern_in_paradigm():
    state = _make_state("S9", {
        "paradigm": "אני צועק ויוצא מהחדר",
        "stance": {"reality_belief": "העולם מסוכן"},
        "pattern": "כל פעם שמעירים — כעס ובריחה",
        "event_description": "מריבה עם אשתי",
    })
    coach, state = await handle_conversation("", state, "he")

    issues = []
    if "אני צועק ויוצא מהחדר" in coach and "מדויק" in coach:
        issues.append("ACCEPTED_PATTERN_AS_PARADIGM: Confirmed pattern-level content as paradigm")
    return coach, issues


# ── S11: gains about behavior, not belief → should redirect ──────────────────

@regression("s11_behavior_gains", "S11: Gains about behavior (not belief) should prompt redirect to belief level")
async def test_s11_behavior_gains():
    state = _make_state("S11", {
        "stance": {
            "reality_belief": "אנשים תמיד ישפטו אותי",
            "gains": ["השתיקה נותנת לי שקט", "לא נכנס לריבים"],
            "losses": ["בדידות", "לא מתקדם בעבודה"],
        },
        "paradigm": "ככה זה אצלי — עדיף לשתוק",
        "pattern": "שתיקה והימנעות",
    })
    coach, state = await handle_conversation("", state, "he")

    issues = []
    # Coach should notice gains are about the BEHAVIOR (שתיקה) not the BELIEF
    if "השתיקה נותנת" in coach and not _contains_any(coach, ["אמונה", "תפיסה", "האמונה"]):
        issues.append("BEHAVIOR_LEVEL: Reflected behavior-level gains without redirecting to belief level")
    return coach, issues


# ── S14→S15: warm statement, no question ────────────────────────────────────

@regression("s14_to_s15_no_question", "S14→S15: After vision, warm statement — NOT 'מה המחויבות?'")
async def test_s14_to_s15_no_question():
    state = _make_state("S14", {
        "renewal": "אני בוחר להאמין שאני ראוי",
        "vision": "",
        "event_description": "מריבה עם אשתי",
        "pattern": "בריחה מביקורת",
    })
    coach, state = await handle_conversation(
        "אני רואה את עצמי מגיע הביתה, מדבר עם אשתי ברוגע, מקשיב לה בלי לברוח. יש לנו ערב שקט יחד.",
        state, "he"
    )

    issues = []
    if _contains_any(coach, ["מה המחויבות", "מה הצעד", "מה תעשה מחר"]) and _has_question(coach):
        issues.append("ASKED_COMMITMENT: Asked commitment question instead of warm statement + card")
    return coach, issues


# ── S15: vague commitment should not pass ────────────────────────────────────

@regression("s15_vague_commitment", "S15: 'אנסה להשתפר' should trigger specificity request")
async def test_s15_vague_commitment():
    state = _make_state("S15", {
        "commitment": "אנסה להשתפר",
        "renewal": "אני בוחר להאמין שאני ראוי",
        "event_description": "מריבה עם אשתי",
    })
    coach, state = await handle_conversation("", state, "he")

    issues = []
    if "אנסה להשתפר" in coach and not _has_question(coach):
        issues.append("ACCEPTED_VAGUE: Accepted vague commitment without asking for specifics")
    return coach, issues


# ── Cross-cutting: response length ──────────────────────────────────────────

@regression("response_length", "General: Coach response should not exceed 500 chars in V3")
async def test_response_length():
    state = _make_state("S3", {
        "emotions": ["כעס", "תסכול", "עלבון"],
        "event_description": "אתמול אשתי צעקה עלי שאני לא עושה כלום בבית"
    })
    coach, state = await handle_conversation("", state, "he")

    issues = []
    if len(coach) > 500:
        issues.append(f"TOO_LONG: Response is {len(coach)} chars (max 500 for V3)")
    return coach, issues


# ── Cross-cutting: no inventing content ─────────────────────────────────────

@regression("no_invented_content", "General: Coach should not add details user never said")
async def test_no_invented_content():
    state = _make_state("S4", {
        "emotions": ["כעס"],
        "event_description": "מריבה עם אשתי",
        "topic": "זוגיות"
    })
    coach, state = await handle_conversation("חשבתי שאני כישלון", state, "he")

    issues = []
    # Coach should not add things like "בגלל ש...", "כנראה ש...", "אתה מרגיש ש..."
    invented_patterns = ["כנראה ש", "ייתכן ש", "נראה שאתה", "בגלל ש", "זה מראה ש"]
    for pat in invented_patterns:
        if pat in coach:
            issues.append(f"INVENTED: Coach added '{pat}' — interpreting beyond what user said")
            break
    return coach, issues


# ── Cross-cutting: no technical terms leaked ────────────────────────────────

@regression("no_technical_leak", "General: No S0/S1/current_step/gate/saturation in coach response")
async def test_no_technical_leak():
    state = _make_state("S7", {
        "gap_name": "ביטול עצמי",
        "gap_score": "7",
        "event_description": "מריבה עם אשתי",
    })
    coach, state = await handle_conversation("", state, "he")

    issues = []
    for term in ["current_step", "gate", "saturation", "S7", "S8", "collected_data"]:
        if term in coach:
            issues.append(f"TECHNICAL_LEAK: '{term}' appeared in coach response")
    return coach, issues


# ═══════════════════════════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

async def run_tests(test_filter: str = None, verbose: bool = False):
    tests_to_run = TESTS
    if test_filter:
        tests_to_run = {k: v for k, v in TESTS.items() if test_filter in k}

    if not tests_to_run:
        print(f"❌ No tests matching '{test_filter}'")
        return False

    print(f"\n{'='*70}")
    print(f"  BSD Coaching Regression Tests — {len(tests_to_run)} tests")
    print(f"{'='*70}\n")

    passed = 0
    failed = 0
    errors = 0

    for name, test in tests_to_run.items():
        print(f"  🧪 {name}: {test['desc']}")
        try:
            t0 = time.time()
            coach_response, issues = await test["fn"]()
            elapsed = time.time() - t0

            if issues:
                failed += 1
                print(f"  ❌ FAIL ({elapsed:.1f}s)")
                for issue in issues:
                    print(f"     └─ {issue}")
                if verbose:
                    print(f"     📝 Coach: {coach_response[:200]}...")
            else:
                passed += 1
                print(f"  ✅ PASS ({elapsed:.1f}s)")
                if verbose:
                    print(f"     📝 Coach: {coach_response[:200]}...")
        except Exception as e:
            errors += 1
            print(f"  💥 ERROR: {e}")

        print()

    print(f"{'='*70}")
    print(f"  Results: {passed} passed, {failed} failed, {errors} errors")
    print(f"{'='*70}\n")

    return failed == 0 and errors == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BSD Coaching Regression Tests")
    parser.add_argument("--test", help="Run specific test (substring match)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show coach responses")
    args = parser.parse_args()

    success = asyncio.run(run_tests(args.test, args.verbose))
    sys.exit(0 if success else 1)
