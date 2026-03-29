#!/usr/bin/env python3
"""
סימולציות ממוקדות אחרי תיקוני הפרומפט (S1 הבהרה, S3 רגש שכבר באירוע / גיוון ניסוח).

Usage:
  cd backend && source antenv/bin/activate  # או venv
  python simulate_post_fix_checks.py              # בדיקות פרומפט מורכב בלבד (ללא API)
  python simulate_post_fix_checks.py --live       # + סימולציות מול LLM (דורש deployment תקין)

דורש משתני סביבה ל-Azure OpenAI רק עם --live.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    for p in (Path(__file__).parent.parent / ".env", Path(__file__).parent / ".env"):
        if p.exists():
            load_dotenv(p)
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent))

from app.bsd_v2.single_agent_coach import handle_conversation
from app.bsd_v2.state_schema_v2 import create_initial_state
from app.bsd_v2.prompts.prompt_manager import assemble_system_prompt


def _ok(name: str, cond: bool, detail: str = "") -> bool:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    return cond


def run_offline_prompt_checks() -> list[bool]:
    """
    בודק שהקבצים שנטענים ב-assemble_system_prompt מכילים את התיקונים (בלי קריאת LLM).
    """
    print("\n=== מצב offline: בדיקת פרומפטים מורכבים (S1, S3) ===\n")
    results: list[bool] = []
    s1 = assemble_system_prompt("S1", "he")
    s3 = assemble_system_prompt("S3", "he")

    results.append(
        _ok(
            "S1: כלל הבהרה — לא לקפוץ ל-S2 רק בגלל בקשת הבהרה",
            "בקשת הבהרה" in s1 and ("אל תקפוץ שלב" in s1 or "הישאר/י ב-S1" in s1),
            f"אורך פרומפט S1: {len(s1)}",
        )
    )
    results.append(
        _ok(
            "S3: רגש שכבר בתיאור האירוע + גיוון ניסוח (לא בוטי)",
            "רגש שכבר בתיאור" in s3 and "גיוון ניסוח" in s3,
            f"אורך פרומפט S3: {len(s3)}",
        )
    )

    s1_en = assemble_system_prompt("S1", "en")
    s3_en = assemble_system_prompt("S3", "en")
    results.append(
        _ok(
            "EN S1: clarification / do not skip to S2",
            "clarification" in s1_en.lower() and "do not skip" in s1_en.lower(),
            f"len={len(s1_en)}",
        )
    )
    results.append(
        _ok(
            "EN S3: emotion already in event + vary wording",
            "emotion already" in s3_en.lower() and "robotic" in s3_en.lower(),
            f"len={len(s3_en)}",
        )
    )
    return results


async def scenario_s1_clarification_baize_mitzav() -> list[bool]:
    """
    מחקה קו קרוב לשיחה 140: אחרי שאלה על 'מצב כזה' המשתמש שואל 'באיזה מצב?'.
    ציפייה: לא לקפוץ ל-S2 רק כדי 'למקד אירוע' בלי להבהיר קודם; להישאר ב-S1 או להבהיר במילים של המשתמש.
    """
    print("\n=== תרחיש A: S1 — 'באיזה מצב?' אחרי שאלה כפולת-משמעות ===\n")
    state = create_initial_state("sim-s1-clar", "u1", "he")
    user_turns = [
        "כן",
        "על הנהגת הבית",
        "היכולת שלי ליצור שיתוף פעולה של הילדים בבית במשפחה",
        "שאני לא מצליחה להביא אותם לזה ואז אני מתוסכלת וכועסת",
        "באיזה מצב?",
    ]
    last_coach = ""
    results: list[bool] = []
    for i, msg in enumerate(user_turns):
        last_coach, state = await handle_conversation(msg, state, "he")
        if "בעיה טכנית" in last_coach or "נסות שוב" in last_coach:
            print("  [ABORT] המאמן החזיר הודעת תקלה — ה-LLM לא זמין (בדוק deployment / מפתחות).")
            results.append(_ok("סימולציה חיה — API עובד", False, "תשובת fallback"))
            return results
        step = state.get("current_step", "?")
        print(f"  תור {i+1} | שלב אחרי תגובה: {step}")
        print(f"  מאמן: {last_coach[:220]}{'...' if len(last_coach) > 220 else ''}\n")

    step = state.get("current_step", "")
    # אחרי בקשת הבהרה — לא אמור לדלג ל-S2 רק בגלל זה (כלל ב-s1_topic)
    bad_jump = step == "S2" and (
        "אירוע ספציפי" in last_coach
        or "סיפור" in last_coach
        and "מתי" in last_coach
    )
    # מותר להישאר S1 ולהבהיר; גם אם המודל טעה קלות, נכשל רק אם ברור קפיצה לאירוע בלי הבהרה
    clarifies = any(
        w in last_coach
        for w in ("התכוונתי", "כוונתי", "מצב שבו", "כשאת", "מה שקרה", "המצב")
    )
    results.append(
        _ok(
            "אחרי 'באיזה מצב?' לא מבקשים מיד 'אירוע ספציפי' כתיקון לבלבול (S2 קפיצה גסה)",
            not (step == "S2" and "אירוע" in last_coach and not clarifies),
            f"שלב={step}",
        )
    )
    results.append(
        _ok(
            "יש ניסוח של הבהרה / מיקוד (מילות מפתח)",
            clarifies or step == "S1",
            f"שלב={step}",
        )
    )
    return results


async def scenario_s3_emotion_already_in_event() -> list[bool]:
    """
    אירוע שכבר כולל כעס/תיאור רגשי — תגובת S3 הראשונה צריכה לנעול לולאה, לא 'איך הרגשת' גנרי בלבד.
    """
    print("\n=== תרחיש B: S3 — רגש כבר בתיאור האירוע ===\n")
    state = create_initial_state("sim-s3-loop", "u1", "he")
    user_turns = [
        "כן",
        "גבולות עם הילדים",
        "לומר לא כשהם לוחצים",
        "לפני שבוע בערב בבית. הבת לא עשתה מה שביקשתי. נכנסתי לחדר שלה, כעסתי מאוד והטחתי בה האשמות, היא נשארה שקטה.",
    ]
    last_coach = ""
    for i, msg in enumerate(user_turns):
        last_coach, state = await handle_conversation(msg, state, "he")
        if "בעיה טכנית" in last_coach or "נסות שוב" in last_coach:
            print("  [ABORT] המאמן החזיר הודעת תקלה — ה-LLM לא זמין.")
            results: list[bool] = []
            results.append(_ok("סימולציה חיה — API עובד", False, "תשובת fallback"))
            return results
        step = state.get("current_step", "?")
        print(f"  תור {i+1} | שלב: {step}")
        print(f"  מאמן: {last_coach[:240]}{'...' if len(last_coach) > 240 else ''}\n")

    results: list[bool] = []
    # אחרי תיאור עם כעסתי — לא לפתוח רק ב"איך הרגשת באותו רגע?" בלי לנעול כעס
    generic_only = (
        "איך הרגשת" in last_coach
        or "מה הרגשת" in last_coach
    ) and not ("כעס" in last_coach or "כועס" in last_coach)
    results.append(
        _ok(
            "מזהים כעס מהטקסט (לולאה) ולא רק שאלה גנרית על רגש",
            not generic_only,
            "אם FAIL — המאמן שאל רגש בלי לחזור על כעס שהמשתמש כבר אמר",
        )
    )
    # גיוון: אם יש שני תורי S3 רצופים עם אותו משפט "ומה עוד הרגשת שם" — אז FAIL רך (לא נבדוק כאן כפילות בין שני תורים בלי להריץ תור נוסף)
    return results


async def _async_main(live: bool) -> int:
    """תמיד מריץ בדיקות offline; עם --live מוסיף סימולציות מול LLM."""
    all_pass: list[bool] = []
    all_pass += run_offline_prompt_checks()

    if live:
        if not os.getenv("AZURE_OPENAI_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            print(
                "\n[סימולציה חיה] אין מפתח API — מדלג. הגדר מפתחות או הרץ בלי --live.\n"
            )
        else:
            print("\n--- סימולציות חיות (LLM) ---\n")
            live_a = await scenario_s1_clarification_baize_mitzav()
            live_b = await scenario_s3_emotion_already_in_event()
            all_pass.extend(live_a)
            all_pass.extend(live_b)

    print("\n" + "═" * 56)
    n = sum(all_pass)
    print(f"  סה\"כ בדיקות שעברו: {n}/{len(all_pass)}")
    print("═" * 56)
    return 0 if n == len(all_pass) else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="בדיקות פרומפט וסימולציית מאמן BSD V2")
    parser.add_argument(
        "--live",
        action="store_true",
        help="בנוסף לבדיקות הפרומפט — הרץ סימולציות מול LLM (דורש deployment תקין)",
    )
    args = parser.parse_args()
    exit_code = asyncio.run(_async_main(live=args.live))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
