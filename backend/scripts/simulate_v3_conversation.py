"""
V3 Conversation Simulator — drives real LLM calls through handle_conversation()
to test prompt quality, stage boundaries, and BSD concept clarity.

Usage:
    cd backend
    .venv/bin/python scripts/simulate_v3_conversation.py
    .venv/bin/python scripts/simulate_v3_conversation.py --stages S2-S5
    .venv/bin/python scripts/simulate_v3_conversation.py --verbose
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
from app.bsd_v2.stage_tool_triggers import resolve_post_turn_tool_call, mark_matzui_summary_sent

# ─── Simulated scenario: conflict with a colleague ───────────────────────────

TOOL_SUBMISSIONS = {
    "S2": {
        "event_description": "אתמול בישיבת צוות, המנהל שלי העיר לי מול כולם שהדוח שלי לא מספיק טוב. אמרתי 'אני אשפר' אבל בפנים הרגשתי שהאדמה נשמטת",
        "topic": "יחסים בעבודה — התמודדות עם ביקורת",
    },
    "S3": {
        "emotions": ["עלבון", "בושה", "כעס"],
    },
    "S5": {
        "action_actual": "ישבתי בשקט, הנהנתי, אמרתי 'אני אשפר' בקול שקט, ואחרי הישיבה הלכתי לחדר שלי וסגרתי את הדלת",
    },
    "S6": {
        "emotion_desired": "ביטחון עצמי, שלווה",
        "thought_desired": "הביקורת היא על הדוח, לא עלי כאדם",
        "action_desired": "להסתכל לו בעיניים ולומר 'אני שמח שאתה אומר — בוא נדבר על הפרטים אחרי הישיבה'",
    },
    "S7": {
        "gap_name": "ביטול עצמי",
        "gap_score": "8",
        "gap_booklet_moves": ["belief", "opportunity"],
    },
    "S9": {
        "paradigm": "ככה זה אצלי — אם מישהו מעיר לי, זה אומר שאני לא מספיק טוב, אז עדיף לשתוק ולהיעלם",
        "stance": {"reality_belief": "העולם מודד אותך לפי הטעויות שלך. אם נתפסת בטעות — איבדת את הערך שלך."},
    },
}

FREE_CHAT_RESPONSES = {
    "S4": "עברה לי המחשבה 'הנה, שוב הוכחתי שאני לא מספיק טוב. כולם ראו את זה. אני חייב להיעלם מפה כמה שיותר מהר'",
    "S8": "כן, אני מזהה את הדפוס הזה גם עם אשתי — כשהיא מעירה לי על משהו, אני מיד נסגר ונעלם. גם עם ההורים שלי — תמיד שותק ומבליע. כל פעם שמישהו אומר משהו שנשמע כמו ביקורת, אני פשוט נעלם פנימה",
    "S4_confirm": "כן, זה מדויק",
    "S5_confirm": "כן, בדיוק ככה זה היה",
}

# ─── Stage-jump detection keywords ──────────────────────────────────────────

NEXT_STAGE_MARKERS = {
    "S2": ["הרגשת", "רגש", "מה הרגשת"],
    "S3": ["מחשבה", "אמירה פנימית", "מה עבר לך", "מה אמרת לעצמך", "בראש"],
    "S4": ["מה עשית", "פעולה", "עשית בפועל", "צופה מבחוץ"],
    "S5": ["היית רוצה", "רצוי", "מה שהיית", "מה היית רוצה"],
    "S6": ["פער", "שם לפער", "כותרת"],
    "S7": ["דפוס", "מזהה את עצמך", "עוד מקומות", "חוזר"],
    "S8": ["ככה זה אצלי", "חוק פנימי", "פרדיגמה", "מה מפעיל"],
}

CONCEPT_CONFUSION_PATTERNS = [
    (r"פרדיגמה.*דפוס|דפוס.*פרדיגמה", "mixing paradigm and pattern"),
    (r"עמדה.*פרדיגמה.*אותו דבר|הפרדיגמה.*היא.*העמדה", "equating paradigm and stance"),
]

RE_ASK_PATTERNS = {
    "S2": ["ספר לי על אירוע", "מתי זה קרה", "עם מי"],
    "S3": ["מה הרגשת", "איזה רגשות"],
    "S5": ["מה עשית בפועל"],
    "S6": ["מה היית רוצה להרגיש", "מה היית רוצה לחשוב"],
    "S7": ["תן שם לפער", "מה הציון"],
    "S9": ["מהי הפרדיגמה שלך", "מהי העמדה שלך"],
}


CARD_STAGES = {"S2", "S3", "S5", "S6", "S7", "S9", "S11", "S12", "S13", "S15"}
CHAT_STAGES = {"S4", "S8", "S14"}

# Expected bridging: stage → next stage's keywords (these are ALLOWED, not bugs)
EXPECTED_BRIDGING = {
    "S3": {"S4": ["מה עבר לך", "אמירה פנימית", "בראש"]},
    "S7": {"S8": ["דפוס", "מזהה את עצמך", "עוד מקומות"]},
}

# What the card collects — used to detect "open then closed"
CARD_TOPICS = {
    "emotion_selector": ["רגש", "הרגשת", "מה הרגשת"],
    "action_field": ["עשית", "פעולה", "מה עשית"],
    "comparison_card": ["היית רוצה", "רצוי"],
    "gap_card": ["פער", "שם לפער", "כותרת"],
    "sentence_builder": ["ככה זה אצלי", "פרדיגמה", "חוק פנימי"],
    "balance_scale": ["מרוויח", "מפסיד", "רווח", "הפסד"],
    "commitment_card": ["מחויבות", "מתחייב", "צעד"],
}


def check_response(stage: str, response: str, new_step: str = None,
                   tool_call: dict = None, is_tool_submission: bool = False) -> list[dict]:
    """Check a coach response for problems. Returns list of issues."""
    issues = []
    resp_lower = response.lower() if response else ""
    has_question = "?" in response

    # 1. Stage jumping — but exclude EXPECTED bridging questions
    next_markers = NEXT_STAGE_MARKERS.get(stage, [])
    expected = EXPECTED_BRIDGING.get(stage, {})
    expected_keywords = []
    for target_stage, keywords in expected.items():
        if new_step == target_stage or new_step == stage:
            expected_keywords.extend(keywords)

    for marker in next_markers:
        if marker in resp_lower and has_question:
            if marker in expected_keywords:
                continue  # This is an expected bridging question, not a bug
            issues.append({
                "type": "STAGE_JUMP",
                "severity": "HIGH",
                "detail": f"Asks '{marker}' (next-stage question) while in {stage}",
                "quote": _extract_question(response, marker),
            })

    # 2. Concept confusion
    for pattern, desc in CONCEPT_CONFUSION_PATTERNS:
        if re.search(pattern, resp_lower):
            issues.append({
                "type": "CONCEPT_CONFUSION",
                "severity": "HIGH",
                "detail": desc,
                "quote": response[:150],
            })

    # 3. Re-asking collected data (only if phrased as a question)
    re_ask = RE_ASK_PATTERNS.get(stage, [])
    for phrase in re_ask:
        idx = resp_lower.find(phrase)
        if idx >= 0:
            nearby = response[idx:idx + 100]
            if "?" in nearby:
                issues.append({
                    "type": "RE_ASK",
                    "severity": "MEDIUM",
                    "detail": f"Re-asks '{phrase}' which tool already collected",
                    "quote": nearby.strip()[:120],
                })

    # 4. STATEMENT_NO_CARD: coach gives statement (no ?) but no card attached
    # Only applies when transitioning to a card stage
    target = new_step or stage
    if not has_question and not tool_call and target in CARD_STAGES:
        issues.append({
            "type": "STATEMENT_NO_CARD",
            "severity": "HIGH",
            "detail": f"Coach gives statement without question, and no card attached (target={target}). User stuck.",
            "quote": response[-100:].strip(),
        })

    # 5. OPEN_THEN_CLOSED: coach asks a question AND card is about to appear on same topic
    if has_question and tool_call:
        tool_type = tool_call.get("tool_type", "")
        card_keywords = CARD_TOPICS.get(tool_type, [])
        for kw in card_keywords:
            if kw in resp_lower:
                # Find the question containing this keyword
                sentences = re.split(r'[.!\n]', response)
                for s in sentences:
                    if kw in s.lower() and "?" in s:
                        issues.append({
                            "type": "OPEN_THEN_CLOSED",
                            "severity": "HIGH",
                            "detail": f"Coach asks '{kw}' in text AND {tool_type} card asks the same",
                            "quote": s.strip()[:120],
                        })
                        break
                break

    # 6. REPETITION: same phrase (8+ chars) appears twice
    words = response.split()
    for i in range(len(words) - 3):
        phrase = " ".join(words[i:i+4])
        if len(phrase) >= 8 and response.count(phrase) > 1:
            issues.append({
                "type": "REPETITION",
                "severity": "MEDIUM",
                "detail": f"Phrase repeated: '{phrase}'",
                "quote": phrase,
            })
            break  # One repetition finding is enough

    # 7. Generic/vague (very short response)
    if len(response.strip()) < 30:
        issues.append({
            "type": "GENERIC",
            "severity": "LOW",
            "detail": f"Response too short ({len(response.strip())} chars)",
            "quote": response.strip(),
        })

    # 8. ANALYTICAL_QUESTION: forbidden causal/analytical patterns
    analytical_patterns = ["איך.*השפיע", "מה גרם ל", "למה הגבת", "מה בהתנהגות.*גרם"]
    for pat in analytical_patterns:
        if re.search(pat, resp_lower):
            issues.append({
                "type": "ANALYTICAL_Q",
                "severity": "HIGH",
                "detail": f"Forbidden analytical question pattern: '{pat}'",
                "quote": _extract_question(response, pat.split(".*")[0]),
            })

    return issues


def _extract_question(text: str, keyword: str) -> str:
    """Extract the sentence containing the keyword."""
    sentences = re.split(r'[.!?\n]', text)
    for s in sentences:
        if keyword in s.lower():
            return s.strip()[:120]
    return text[:120]


STAGE_ORDER = ["S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"]

async def run_simulation(stages: list[str], verbose: bool):
    state = create_initial_state("sim-1", "sim-user", "he")
    state["current_step"] = "S2"
    state["ux_version"] = 3
    state["collected_data"]["topic"] = "יחסים בעבודה — התמודדות עם ביקורת"
    state["collected_data"]["event_description"] = TOOL_SUBMISSIONS["S2"]["event_description"]

    results = []
    all_issues = []

    for stage in stages:
        if stage not in STAGE_ORDER:
            print(f"  ⚠️  Unknown stage {stage}, skipping")
            continue

        print(f"\n{'═' * 60}")
        print(f"  STAGE {stage}")
        print(f"{'═' * 60}")

        # Inject tool data if this stage has a tool
        if stage in TOOL_SUBMISSIONS:
            td = TOOL_SUBMISSIONS[stage]
            cd = state["collected_data"]
            for k, v in td.items():
                if k == "stance" and isinstance(v, dict):
                    cd.setdefault("stance", {}).update(v)
                elif k in cd or k in ("topic",):
                    cd[k] = v
            state["_tool_just_submitted"] = stage
            summary = f"[הגשת כלי: {stage}] " + json.dumps(td, ensure_ascii=False)[:200]
        elif stage in FREE_CHAT_RESPONSES:
            summary = FREE_CHAT_RESPONSES[stage]
        else:
            print(f"  ⚠️  No data for {stage}, skipping")
            continue

        prev_step = state.get("current_step", stage)
        state["current_step"] = stage
        is_tool_sub = stage in TOOL_SUBMISSIONS

        t0 = time.time()
        try:
            coach_msg, state = await handle_conversation(
                user_message=summary,
                state=state,
                language="he",
                user_gender="male",
                conversation_id=999,
            )
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            results.append({"stage": stage, "status": "ERROR", "error": str(e)})
            continue
        elapsed = time.time() - t0

        new_step = state.get("current_step", stage)

        # Resolve tool_call — same as production flow
        tool_sub_type = stage if is_tool_sub else None
        tool_call = resolve_post_turn_tool_call(
            prev_step, state, ux_version=3,
            from_tool_submission=tool_sub_type,
        )
        if tool_call and tool_call.get("tool_type") == "matzui_summary":
            mark_matzui_summary_sent(state)

        issues = check_response(stage, coach_msg, new_step=new_step,
                                tool_call=tool_call, is_tool_submission=is_tool_sub)
        status = "FAIL" if any(i["severity"] == "HIGH" for i in issues) else "WARN" if issues else "PASS"
        icon = "❌" if status == "FAIL" else "⚠️" if status == "WARN" else "✅"
        tool_info = f" + {tool_call['tool_type']}" if tool_call else ""

        print(f"  {icon} {status} | step: {stage}→{new_step}{tool_info} | {elapsed:.1f}s | {len(coach_msg)} chars")

        if verbose or status != "PASS":
            print(f"  Coach: {coach_msg[:300]}{'...' if len(coach_msg) > 300 else ''}")

        for issue in issues:
            sev = issue['severity']
            print(f"  {'🔴' if sev == 'HIGH' else '🟡' if sev == 'MEDIUM' else '🔵'} [{issue['type']}] {issue['detail']}")
            print(f"     → \"{issue['quote']}\"")

        results.append({"stage": stage, "status": status, "step_after": new_step, "issues": issues, "elapsed": elapsed})
        all_issues.extend(issues)

        # Handle confirmation turns for S4 and S5
        if stage == "S4" and FREE_CHAT_RESPONSES.get("S4_confirm"):
            coach_msg2, state = await handle_conversation(
                user_message=FREE_CHAT_RESPONSES["S4_confirm"],
                state=state, language="he", user_gender="male", conversation_id=999,
            )
            if verbose:
                print(f"  Coach (confirm): {coach_msg2[:200]}")

        if stage == "S5" and FREE_CHAT_RESPONSES.get("S5_confirm"):
            coach_msg2, state = await handle_conversation(
                user_message=FREE_CHAT_RESPONSES["S5_confirm"],
                state=state, language="he", user_gender="male", conversation_id=999,
            )
            if verbose:
                print(f"  Coach (confirm): {coach_msg2[:200]}")

    # ─── Final Report ────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  SIMULATION REPORT")
    print(f"{'═' * 60}")

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    warned = sum(1 for r in results if r["status"] == "WARN")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    print(f"  Stages tested: {len(results)}")
    print(f"  ✅ Pass: {passed}  ⚠️ Warn: {warned}  ❌ Fail: {failed}  💥 Error: {errors}")

    if all_issues:
        print(f"\n  Issues by type:")
        from collections import Counter
        for itype, count in Counter(i["type"] for i in all_issues).most_common():
            print(f"    {itype}: {count}")

    high_issues = [i for i in all_issues if i["severity"] == "HIGH"]
    if high_issues:
        print(f"\n  🔴 HIGH severity issues ({len(high_issues)}):")
        for i in high_issues:
            print(f"    - [{i['type']}] {i['detail']}")

    total_time = sum(r.get("elapsed", 0) for r in results)
    print(f"\n  Total LLM time: {total_time:.1f}s (avg {total_time/max(len(results),1):.1f}s/stage)")

    return 1 if failed or errors else 0


def parse_stage_range(s: str) -> list[str]:
    """Parse 'S2-S5' or 'S3,S5,S9' into list of stages."""
    if "-" in s:
        start, end = s.split("-")
        si = STAGE_ORDER.index(start)
        ei = STAGE_ORDER.index(end)
        return STAGE_ORDER[si:ei + 1]
    return [x.strip() for x in s.split(",")]


def main():
    parser = argparse.ArgumentParser(description="V3 Conversation Simulator")
    parser.add_argument("--stages", default="S2-S9", help="Stage range: S2-S9 or S3,S5,S9")
    parser.add_argument("--verbose", action="store_true", help="Print full responses")
    args = parser.parse_args()

    stages = parse_stage_range(args.stages)
    print(f"V3 Conversation Simulator — stages: {', '.join(stages)}")
    print(f"Scenario: Workplace conflict — criticism from manager in team meeting\n")

    exit_code = asyncio.run(run_simulation(stages, args.verbose))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
