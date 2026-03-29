#!/usr/bin/env python3
"""
סימולציות לשלב S1 — נושא אימון לפי החוברת (5 תנאים), מניעת „מריחה“ / רגש־בלבד / אשכול מפוזר.

כללים (מתוך prompts/stages/s1_topic.md):
  נושא תקף: נובע משינוי, סובב קושי, מטרה בלשון חיובית, תוצאה מדידה, דרכי פעולה.
  לא נושא: רגש בלבד; אשכול רעיונות מפוזר — לבקש מיקוד („משפט אחד“ / „מה הכי מאתגר“).
  S1 בלי מצב כיום/רצוי וללא שאלות רגש על „אותו רגע“.

Usage:
  cd backend && antenv/bin/python simulate_s1_topic_cases.py           # offline בלבד
  cd backend && antenv/bin/python simulate_s1_topic_cases.py --live # + סימולציות LLM
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
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

from app.bsd_v2.prompts.prompt_manager import assemble_system_prompt
from app.bsd_v2.single_agent_coach import handle_conversation
from app.bsd_v2.state_schema_v2 import create_initial_state


def _ok(name: str, cond: bool, detail: str = "") -> bool:
    tag = "PASS" if cond else "FAIL"
    print(f"  [{tag}] {name}" + (f" — {detail}" if detail else ""))
    return cond


def run_offline_s1_prompt_checks() -> list[bool]:
    print("\n=== Offline: תוכן פרומפט S1 ===\n")
    results: list[bool] = []
    p = assemble_system_prompt("S1", "he")
    results.append(_ok("מזכיר את 5 התנאים / חוברת", "חמשת התנאים" in p or "5" in p))
    results.append(_ok("מפריד רגש בלבד מאשכול מפוזר", "לא נושא" in p and ("רגש" in p or "כבד" in p)))
    results.append(_ok("מיקוד כשיש כמה כיוונים (משפט אחד / מאתגר)", "משפט אחד" in p or "מאתגר" in p))
    results.append(_ok("איסור שאלות מצב כיום/רצוי ב-S1", "מצב כיום" in p or "מצב רצוי" in p))
    return results


def _no_s2_premature(step: str, coach: str, allow_s2: bool) -> bool:
    if allow_s2:
        return True
    if step == "S2" and ("אירוע" in coach or "ספציפי" in coach):
        return False
    return True


async def scenario_emotion_only() -> list[bool]:
    """רגש בלבד — לא לקבל כנושא; לא לשאול רגש באותו רגע; לא לקפוץ ל-S2 מוקדם."""
    print("\n=== תרחיש 1: רגש בלבד („כבד“, בלי נושא ממוקד) ===\n")
    state = create_initial_state("sim-s1-emotion", "u1", "he")
    turns = ["כן", "פשוט כבד לי מאוד, לא יודע להסביר"]
    last = ""
    for i, u in enumerate(turns):
        last, state = await handle_conversation(u, state, "he")
        if "בעיה טכנית" in last:
            return [_ok("API", False, "תקלה")]
        print(f"  תור {i+1} | {state.get('current_step')} | {last[:180]}...\n")
    step = state.get("current_step", "")
    bad_emotion_q = bool(
        re.search(r"מה\s+הרגשת\s+באותו\s+רגע", last)
        or "באותו רגע" in last and "מה הרגשת" in last
    )
    r: list[bool] = []
    r.append(_ok("לא שואלים ‚מה הרגשת באותו רגע‘ ב-S1 (אין אירוע)", not bad_emotion_q))
    r.append(_ok("נשארים ב-S1 או מבקשים מיקוד לנושא (לא S2 מוקדם)", step == "S1" or _no_s2_premature(step, last, False)))
    return r


async def scenario_scattered_cluster() -> list[bool]:
    """אשכול מפוזר — לבקש משפט אחד / מה הכי מאתגר."""
    print("\n=== תרחיש 2: אשכול מפוזר (כמה נושאים בבת אחת) ===\n")
    state = create_initial_state("sim-s1-scatter", "u1", "he")
    turns = ["כן", "דחייה, אנרגיה נמוכה, חשק, גם עבודה וגם בית — הכל"]
    last = ""
    for i, u in enumerate(turns):
        last, state = await handle_conversation(u, state, "he")
        if "בעיה טכנית" in last:
            return [_ok("API", False, "תקלה")]
        print(f"  תור {i+1} | {state.get('current_step')} | {last[:200]}...\n")
    focus = any(
        x in last
        for x in ("משפט אחד", "מה מכל זה", "הכי מאתגר", "מאתגר אותך", "על מה בדיוק", "למקד")
    )
    r: list[bool] = []
    r.append(_ok("מבקש מיקוד / משפט אחד / מה הכי מאתגר (לא מקבלים את האשכול כנושא)", focus))
    r.append(_ok("שלב עדיין S1 אחרי אשכול (לא מעבר ל-S2 בלי נושא ברור)", state.get("current_step") == "S1"))
    return r


async def scenario_valid_topic_then_gate() -> list[bool]:
    """נושא ברור מהר — מותר מעבר ל-S2 אחרי gate."""
    print("\n=== תרחיש 3: נושא ברור (גבולות לילדים) — ציפייה למעבר S2 אחרי דיון קצר ===\n")
    state = create_initial_state("sim-s1-clear", "u1", "he")
    turns = ["כן", "הצבת גבולות לילדים", "כשהם מתחננים אני נכנעת"]
    last = ""
    for i, u in enumerate(turns):
        last, state = await handle_conversation(u, state, "he")
        if "בעיה טכנית" in last:
            return [_ok("API", False, "תקלה")]
        print(f"  תור {i+1} | {state.get('current_step')} | {last[:200]}...\n")
    step = state.get("current_step", "")
    r: list[bool] = []
    r.append(_ok("אחרי נושא ברור מגיעים ל-S2 או מבקשים אירוע (עומדים ב-Gate)", step == "S2" or "אירוע" in last or "רגע" in last))
    return r


async def run_live() -> list[bool]:
    all_r: list[bool] = []
    all_r += await scenario_emotion_only()
    all_r += await scenario_scattered_cluster()
    all_r += await scenario_valid_topic_then_gate()
    return all_r


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()

    results = run_offline_s1_prompt_checks()
    if args.live:
        if not os.getenv("AZURE_OPENAI_API_KEY"):
            print("\nאין AZURE_OPENAI_API_KEY — מדלג על --live")
        else:
            print("\n--- סימולציות חיות S1 ---")
            results.extend(await run_live())

    print("\n" + "═" * 56)
    n = sum(results)
    print(f"  סה\"כ: {n}/{len(results)}")
    print("═" * 56)
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
