#!/usr/bin/env python3
"""
Focused S13 (בחירה/Choice) simulation — starts with pre-filled state from S12.
Tests whether the coach can complete stance→paradigm→pattern and transition to S14.
"""

import sys, os, asyncio, time
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
YELLOW = "\033[93m"; RED = "\033[91m"; CYAN = "\033[96m"; DIM = "\033[2m"


def make_s13_ready_state(persona_key: str) -> dict:
    state = create_initial_state(
        conversation_id=f"s13_test_{persona_key}_{int(time.time())}",
        user_id=f"sim_{persona_key}",
        language="he",
    )
    state["current_step"] = "S13"
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
            "pattern": "כשיש מתח או התנגדות, אני בורח או מוותר",
            "paradigm": "ככה זה אצלי — כשמישהו כועס, אני שומר על קשר רק אם אני לא מתעמת",
            "stance": {
                "reality_belief": "כעס הורס קשרים",
                "activation_trigger": "הרמת קול מול אנשים שחשובים לי",
                "gains": ["שקט", "הימנעות מעימות", "ביטחון"],
                "losses": ["חיבור אמיתי", "כבוד עצמי", "גבולות בריאים"],
            },
            "forces": {
                "source": ["אהבה", "אחריות", "אמת", "חיבור", "חופש", "צמיחה"],
                "nature": ["פחד", "שליטה", "הימנעות", "ביקורתיות", "כעס", "חוסר סבלנות"],
            },
        },
        "career": {
            "topic": "תקיעות בקריירה",
            "event_description": "בישיבת צוות הבוס נתן קידום לקולגה צעיר",
            "emotions": ["כעס", "עלבון", "תסכול", "חוסר אונים"],
            "thought": "אין טעם לריב, בסוף תמיד מעדיפים צעירים",
            "action_actual": "ישבתי בשקט וחייכתי",
            "action_desired": "להגיד לבוס שהובטח לי קידום",
            "gap_name": "שתיקה מול חוסר צדק",
            "gap_score": "9",
            "pattern": "כשמתעלמים ממני, אני שותק ובולע",
            "paradigm": "מי שלא מסתכן, לא מפסיד",
            "stance": {
                "reality_belief": "אם אדרוש, יפטרו אותי",
                "activation_trigger": "כשמישהו מקבל משהו שמגיע לי",
                "gains": ["ביטחון תעסוקתי", "הימנעות מסכסוך"],
                "losses": ["קידום", "הערכה עצמית", "שכר ראוי"],
            },
            "forces": {
                "source": ["אחריות", "חיבור", "אהבה", "צמיחה", "משמעות", "חופש"],
                "nature": ["פחד", "שליטה", "הימנעות", "ביקורתיות", "עצלות", "כעס"],
            },
        },
    }

    cd = PREFILLS.get(persona_key, PREFILLS["parenting"])
    state["collected_data"].update(cd)
    return state


SIMULATOR_PROMPT = """אתה מתאמן בשיחת אימון בעברית. אתה בשלב בחירת עמדה חדשה, פרדיגמה חדשה ודפוס חדש.

## הרקע שלך
{background}

## כללים
1. ענה בעברית טבעית, 1-3 משפטים
2. כשנשאל על עמדה חדשה — תן אמונה חדשה שמחליפה את הישנה
3. כשנשאל על פרדיגמה — תן "ככה זה אצלי" חדש
4. כשנשאל על דפוס חדש — תן פעולה קונקרטית חדשה
5. כשנשאל על כמ"ז/תמהיל — תן תשובה טבעית כמו "בעיקר מתוך אהבה ואחריות"
6. אם המאמן שואל "האם זה משמח?" — ענה בכנות
7. אל תנתח את עצמך — דבר פשוט"""

BACKGROUNDS = {
    "parenting": "אבי, 38, אב לשלושה. עמדה ישנה: כעס הורס קשרים. מקור: אהבה (מובילה), אחריות, אמת, חיבור, חופש, צמיחה. טבע: פחד (מוביל), שליטה, הימנעות, ביקורתיות.",
    "career": "יוסי, 45, רואה חשבון. עמדה ישנה: אם אדרוש יפטרו אותי. מקור: אחריות (מובילה), חיבור, אהבה, צמיחה, משמעות, חופש. טבע: פחד (מוביל), שליטה, הימנעות, ביקורתיות.",
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


async def run_s13_test(persona_key: str, max_turns: int = 15):
    state = make_s13_ready_state(persona_key)
    history = []

    print(f"\n{'═'*60}")
    print(f"{BOLD}🔬 S13 בדיקה ממוקדת: {persona_key}{RESET}")
    print(f"{'═'*60}")

    coach_msg, state = await handle_conversation("בוא נמשיך", state, "he")
    history.append({"sender": "coach", "content": str(coach_msg)})
    print(f"\n{GREEN}🤖 מאמן:{RESET} {str(coach_msg)[:200]}...")

    for turn in range(1, max_turns + 1):
        step = state.get("current_step", "?")
        renewal = state.get("collected_data", {}).get("renewal")

        if step != "S13":
            print(f"\n{GREEN}✅ יצא מ-S13 → {step} אחרי {turn} תורות!{RESET}")
            print(f"   renewal: {renewal}")
            break

        user_msg = await simulate_user(str(coach_msg), history, persona_key)
        coach_msg, state = await handle_conversation(user_msg, state, "he")

        history.append({"sender": "user", "content": user_msg})
        history.append({"sender": "coach", "content": str(coach_msg)})

        sat = state.get("saturation_score", 0)
        renewal_status = "✓" if renewal else "✗"
        print(f"\n{DIM}─ תור {turn} │ S13 │ renewal:{renewal_status} │ רוויה:{sat:.2f}{RESET}")
        print(f"{CYAN}👤{RESET} {user_msg[:120]}")
        print(f"{GREEN}🤖{RESET} {str(coach_msg)[:180]}...")
    else:
        print(f"\n{RED}❌ לא יצא מ-S13 ב-{max_turns} תורות{RESET}")
        print(f"   renewal: {renewal}")


async def main():
    for p in ["parenting", "career"]:
        await run_s13_test(p)
    print(f"\n{'═'*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
