#!/usr/bin/env python3
"""
בדיקת JSON Mode - וידוא שה-LLM מחזיר JSON תקין עם response_format.

הרצה:
  cd backend && source antenv/bin/activate
  python test_json_mode.py

דורש: .env עם AZURE_OPENAI_* (או משתני סביבה)
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent))


async def test_json_mode_real():
    """קריאה אמיתית ל-LLM עם JSON Mode - בודק שהתשובה היא JSON תקין."""
    from langchain_core.messages import SystemMessage, HumanMessage
    from app.bsd.llm import get_azure_chat_llm
    from app.bsd_v2.prompts.prompt_manager import assemble_system_prompt

    if not os.getenv("AZURE_OPENAI_API_KEY"):
        print("⚠️  SKIP: AZURE_OPENAI_API_KEY לא מוגדר")
        return None

    print("=" * 60)
    print("בדיקת JSON Mode - קריאה אמיתית ל-Azure OpenAI")
    print("=" * 60)

    llm = get_azure_chat_llm(purpose="talker")
    if os.getenv("BSD_V2_JSON_MODE", "1").strip() in ("1", "true", "yes"):
        llm = llm.bind(response_format={"type": "json_object"})
        print("✅ JSON Mode מופעל (response_format=json_object)")
    else:
        print("⚠️  JSON Mode כבוי (BSD_V2_JSON_MODE=0)")
        return None

    system_prompt = assemble_system_prompt("S1", "he")
    context = "משתמש: כן\nמאמן: על מה תרצה להתאמן היום?\nמשתמש: זוגיות\n\n# הודעה חדשה\nמשתמש: על שיתוף רגשי"
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=context)]

    try:
        response = await llm.ainvoke(messages)
        raw = (response.content or "").strip()
        print(f"\nתשובה גולמית ({len(raw)} תווים):")
        print(raw[:400] + ("..." if len(raw) > 400 else ""))

        # ניקוי markdown אם יש
        if raw.startswith("```"):
            parts = raw.split("```")
            if len(parts) >= 2:
                raw = parts[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            print(f"\n❌ FAIL: התשובה אינה dict (סוג: {type(parsed).__name__})")
            return False

        has_coach = "coach_message" in parsed or "response" in parsed
        has_state = "internal_state" in parsed or "stage" in parsed
        if has_coach and has_state:
            print(f"\n✅ PASS: JSON תקין - coach_message + internal_state")
            print(f"   coach_message: {(parsed.get('coach_message') or parsed.get('response', ''))[:80]}...")
            print(f"   current_step: {(parsed.get('internal_state') or {}).get('current_step', '?')}")
            return True
        else:
            print(f"\n⚠️  JSON תקין אך חסרים שדות: coach_message={has_coach}, internal_state={has_state}")
            return has_coach  # לפחות coach_message

    except json.JSONDecodeError as e:
        print(f"\n❌ FAIL: Failed to parse JSON: {e}")
        print(f"   Raw start: {raw[:200] if raw else 'empty'}...")
        return False
    except Exception as e:
        print(f"\n❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_json_mode_via_handle():
    """בדיקה דרך handle_conversation - וידוא שאין Failed to parse JSON."""
    from app.bsd_v2.state_schema_v2 import create_initial_state, add_message
    from app.bsd_v2.single_agent_coach import handle_conversation
    import logging
    logging.getLogger("app").setLevel(logging.WARNING)

    if not os.getenv("AZURE_OPENAI_API_KEY"):
        print("⚠️  SKIP: AZURE_OPENAI_API_KEY לא מוגדר")
        return None

    print("\n" + "=" * 60)
    print("בדיקה דרך handle_conversation (זוגיות)")
    print("=" * 60)

    state = create_initial_state("test-json", "test-user", "he")
    state["current_step"] = "S0"
    state = add_message(state, "user", "כן")
    state = add_message(state, "coach", "על מה תרצה להתאמן היום?", {"current_step": "S1"})

    try:
        coach_msg, updated_state = await handle_conversation("זוגיות", state, "he")
        print(f"\nתגובה: {coach_msg[:100]}...")
        print(f"שלב: {updated_state['current_step']}")
        print("✅ PASS: handle_conversation החזיר תגובה תקינה")
        return True
    except Exception as e:
        print(f"\n❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    results = []
    r1 = await test_json_mode_real()
    if r1 is not None:
        results.append(("JSON Mode (real LLM)", r1))

    r2 = await test_json_mode_via_handle()
    if r2 is not None:
        results.append(("handle_conversation", r2))

    print("\n" + "=" * 60)
    print("סיכום")
    print("=" * 60)
    for name, ok in results:
        print(f"  {'✅' if ok else '❌'} {name}")
    if not results:
        print("  (אין בדיקות - הגדר AZURE_OPENAI_API_KEY)")
    all_ok = all(ok for _, ok in results)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
