#!/usr/bin/env python3
"""
Focused S12 (KaMaZ/Forces) simulation — starts with pre-filled state from S11.
Tests whether the coach can complete the forces exploration and transition to S13.
Runs in ~2-3 minutes instead of ~15.
"""

import sys, os, asyncio, time, json
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")
os.environ["BSD_V2_SAFETY_NET_DISABLED"] = "1"

from app.bsd_v2.single_agent_coach import handle_conversation
from app.bsd_v2.state_schema_v2 import create_initial_state
from app.bsd.llm import _build_azure_llm

RESET = "\033[0m"; BOLD = "\033[1m"; GREEN = "\033[92m"
YELLOW = "\033[93m"; RED = "\033[91m"; CYAN = "\033[96m"; DIM = "\033[2m"; MAGENTA = "\033[95m"


def make_s12_ready_state(persona_key: str) -> dict:
    """Create a state pre-filled through S11, ready to enter S12."""
    state = create_initial_state(
        conversation_id=f"s12_test_{persona_key}_{int(time.time())}",
        user_id=f"sim_{persona_key}",
        language="he",
    )
    state["current_step"] = "S12"
    state["saturation_score"] = 0.3

    PREFILLS = {
        "parenting": {
            "topic": "הצבת גבולות לילדים",
            "event_description": "אתמול בערב הבן בן 9 סירב לעשות שיעורי בית ואני ויתרתי",
            "emotions": ["פחד", "לחץ", "אשמה", "תסכול"],
            "thought": "אין לי כוח עכשיו לצעקות",
            "action_actual": "אמרתי טוב אז תעשה מחר והלכתי למטבח",
            "action_desired": "להישאר שם, לדבר בקול רגוע אבל ברור",
            "gap_name": "בריחה מעימות",
            "gap_score": "8",
            "pattern": "כשיש מתח או התנגדות מול אנשים קרובים, אני בורח או מוותר כדי לשמור על שקט",
            "paradigm": "ככה זה אצלי — כשמישהו כועס, אני שומר על קשר רק אם אני לא מתעמת",
            "stance": {
                "reality_belief": "כעס הורס קשרים",
                "activation_trigger": "הרמת קול או התנגדות מול אנשים שחשובים לי",
                "gains": ["שקט", "הימנעות מעימות", "תחושת ביטחון"],
                "losses": ["חיבור אמיתי", "כבוד עצמי", "גבולות בריאים לילדים"],
            },
        },
        "career": {
            "topic": "תקיעות בקריירה",
            "event_description": "בישיבת צוות הבוס נתן קידום לקולגה צעיר ויוסי לא אמר מילה",
            "emotions": ["כעס", "עלבון", "תסכול", "חוסר אונים"],
            "thought": "אין טעם לריב, בסוף תמיד מעדיפים צעירים",
            "action_actual": "ישבתי בשקט, חייכתי, ואחרי הישיבה הלכתי לשתות קפה לבד",
            "action_desired": "להגיד לבוס שהובטח לי קידום ולבקש הסבר",
            "gap_name": "שתיקה מול חוסר צדק",
            "gap_score": "9",
            "pattern": "כשמתעלמים ממני או עושים לי עוול, אני שותק ובולע במקום לדרוש",
            "paradigm": "ככה זה אצלי — מי שלא מסתכן, לא מפסיד",
            "stance": {
                "reality_belief": "אם אני אדרוש, יפטרו אותי",
                "activation_trigger": "כשמישהו מקבל משהו שמגיע לי",
                "gains": ["ביטחון תעסוקתי", "הימנעות מסכסוך"],
                "losses": ["קידום", "הערכה עצמית", "שכר ראוי"],
            },
        },
        "wellbeing": {
            "topic": "קושי לומר לא ללקוחות",
            "event_description": "אתמול לקוח התקשר ב-11 בלילה עם שינויים דחופים ונועה ישבה לעבוד",
            "emotions": ["כעס", "תשישות", "תסכול", "בדידות"],
            "thought": "אם אגיד לא, הוא ימצא מישהו אחר",
            "action_actual": "פתחתי את המחשב וישבתי לעבוד עד שתיים בלילה",
            "action_desired": "להגיד שזה לא זמן לעבודה ושאחזור אליו מחר בבוקר",
            "gap_name": "ויתור על עצמי",
            "gap_score": "9",
            "pattern": "כשמבקשים ממני משהו, אני מסכימה גם כשזה על חשבוני",
            "paradigm": "ככה זה אצלי — אם אסרב, אני אאבד אנשים",
            "stance": {
                "reality_belief": "הערך שלי נמדד במה שאני נותנת",
                "activation_trigger": "כשמישהו מבקש ממני משהו בטון דחוף",
                "gains": ["תחושת חשיבות", "לקוחות נשארים"],
                "losses": ["בריאות", "חיים אישיים", "כבוד עצמי"],
            },
        },
    }

    cd = PREFILLS.get(persona_key, PREFILLS["parenting"])
    state["collected_data"].update(cd)
    return state


SIMULATOR_PROMPT = """אתה מתאמן בשיחת אימון בעברית. אתה עכשיו בשלב זיהוי כוחות מקור (ערכים, אור) וכוחות טבע (כבדות, הגנות).

## הרקע שלך
{background}

## כללים
1. ענה בעברית טבעית, 1-3 משפטים
2. כשנשאל על כוחות מקור (ערכים, אור) — תן 1-2 ערכים בכל פעם: אמת, אחריות, חיבור, אהבה, חופש, יצירתיות, צמיחה, משמעות
3. כשנשאל על כוחות טבע (כבדות, הגנות, דחפים) — תן 1-2: פחד, שליטה, הימנעות, כעס, ביקורתיות, עצלות, חוסר סבלנות
4. אם המאמן מסכם — אשר או תקן
5. אל תנתח את עצמך — דבר פשוט"""


BACKGROUNDS = {
    "parenting": "אבי, 38, מנהל בהייטק, אב לשלושה. נושא: קושי להציב גבולות לילדים. גדל עם אבא שצעק.",
    "career": "יוסי, 45, רואה חשבון. מרגיש תקוע 15 שנה. מפחד מהלא-נודע. אביו פוטר.",
    "wellbeing": "נועה, 28, מעצבת גרפית פרילנסרית. לחץ כרוני. מפחדת שאם תסרב ללקוח הוא יעזוב.",
}


async def simulate_user(coach_msg: str, history: list, persona_key: str) -> str:
    prompt = SIMULATOR_PROMPT.format(background=BACKGROUNDS.get(persona_key, BACKGROUNDS["parenting"]))

    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    messages = [SystemMessage(content=prompt)]
    for m in history[-10:]:
        if m["sender"] == "coach":
            messages.append(HumanMessage(content=f"[מאמן]: {m['content']}"))
        else:
            messages.append(AIMessage(content=m["content"]))
    messages.append(HumanMessage(content=f"[מאמן]: {coach_msg}\n\nענה:"))

    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
    llm = _build_azure_llm(deployment=deployment, temperature=0.7)
    response = await llm.ainvoke(messages)
    return response.content.strip()


async def run_s12_test(persona_key: str, max_turns: int = 20):
    state = make_s12_ready_state(persona_key)
    history = []
    forces_log = []

    print(f"\n{'═'*60}")
    print(f"{BOLD}🔬 S12 בדיקה ממוקדת: {persona_key}{RESET}")
    print(f"{'═'*60}")

    # First turn: coach opens S12
    coach_msg, state = await handle_conversation("בוא נמשיך", state, "he")
    history.append({"sender": "coach", "content": str(coach_msg)})
    print(f"\n{GREEN}🤖 מאמן:{RESET} {str(coach_msg)[:150]}...")

    for turn in range(1, max_turns + 1):
        step = state.get("current_step", "?")
        forces = state.get("collected_data", {}).get("forces", {})
        src = forces.get("source", [])
        nat = forces.get("nature", [])
        forces_log.append({"turn": turn, "src": len(src), "nat": len(nat), "step": step})

        # Check if we passed S12
        if step not in ("S12",):
            print(f"\n{GREEN}✅ יצא מ-S12 → {step} אחרי {turn} תורות!{RESET}")
            print(f"   מקור: {len(src)} כוחות | טבע: {len(nat)} כוחות")
            break

        user_msg = await simulate_user(str(coach_msg), history, persona_key)

        coach_msg, state = await handle_conversation(user_msg, state, "he")

        history.append({"sender": "user", "content": user_msg})
        history.append({"sender": "coach", "content": str(coach_msg)})

        sat = state.get("saturation_score", 0)
        print(f"\n{DIM}─ תור {turn} │ S12 │ מקור:{len(src)} טבע:{len(nat)} │ רוויה:{sat:.2f}{RESET}")
        print(f"{CYAN}👤{RESET} {user_msg[:100]}")
        print(f"{GREEN}🤖{RESET} {str(coach_msg)[:150]}...")
    else:
        forces = state.get("collected_data", {}).get("forces", {})
        src = forces.get("source", [])
        nat = forces.get("nature", [])
        print(f"\n{RED}❌ לא יצא מ-S12 ב-{max_turns} תורות{RESET}")
        print(f"   מקור: {len(src)} → {src}")
        print(f"   טבע:  {len(nat)} → {nat}")

    # Summary
    print(f"\n{BOLD}מעקב כוחות:{RESET}")
    for f in forces_log:
        bar_s = "█" * f["src"]
        bar_n = "▓" * f["nat"]
        print(f"  תור {f['turn']:2d} │ מקור: {bar_s:<8} {f['src']} │ טבע: {bar_n:<8} {f['nat']} │ {f['step']}")


async def main():
    personas = ["parenting", "career", "wellbeing"]
    for p in personas:
        await run_s12_test(p)
    print(f"\n{'═'*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
