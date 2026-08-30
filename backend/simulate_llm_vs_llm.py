#!/usr/bin/env python3
"""
LLM-vs-LLM Coaching Simulation
================================
Runs a simulated user (LLM) against the BSD V2 coaching model.
Each persona is a realistic profile with topic, background, emotional style,
and communication patterns drawn from the existing coaching domain.

Usage:
    python simulate_llm_vs_llm.py                    # Run all personas
    python simulate_llm_vs_llm.py --persona parenting # Run a specific persona
    python simulate_llm_vs_llm.py --list              # List available personas
    python simulate_llm_vs_llm.py --max-turns 40      # Override turn limit
"""

import sys
import os
import asyncio
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# ── Setup paths & env ─────────────────────────────────────────────────────────
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

os.environ.setdefault("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
os.environ.setdefault("AZURE_OPENAI_TIMEOUT_SECONDS", "45")
os.environ.setdefault("AZURE_OPENAI_MAX_RETRIES", "2")
# Match production: safety net disabled (it causes oscillations when enabled)
os.environ["BSD_V2_SAFETY_NET_DISABLED"] = "1"

from app.bsd_v2.single_agent_coach import handle_conversation
from app.bsd_v2.state_schema_v2 import create_initial_state
from app.bsd_v2.station_checkpoint import apply_station_intent
from app.bsd_v2.stage_intro_schema import (
    MACRO_STAGE_END_STEPS,
    MACRO_STAGE_START_STEPS,
    MACRO_STAGE_IDS,
    step_to_macro_stage,
    next_macro_stage,
)
from app.bsd.llm import _build_azure_llm

# ── ANSI colors ───────────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"
MAGENTA = "\033[95m"

# ── Stage definitions ─────────────────────────────────────────────────────────
ALL_STAGES = ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8",
              "S9", "S10", "S11", "S12", "S13", "S14", "S15"]

STAGE_NAMES_HE = {
    "S0": "הסכם",    "S1": "נושא",     "S2": "אירוע",    "S3": "רגשות",
    "S4": "מחשבה",   "S5": "מצוי",     "S6": "רצוי",     "S7": "פער",
    "S8": "דפוס",    "S9": "פרדיגמה",  "S10": "עמדה",    "S11": "רווח/הפסד",
    "S12": "כוחות",  "S13": "בחירה",   "S14": "חזון",    "S15": "מחויבות",
}

COLLECTED_DATA_FIELDS = [
    "topic", "event_description", "emotions", "thought",
    "action_actual", "action_desired", "gap_name", "gap_score",
    "pattern", "paradigm", "renewal", "vision", "commitment",
]

# ══════════════════════════════════════════════════════════════════════════════
# PERSONA DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════

PERSONAS: Dict[str, Dict[str, Any]] = {
    "parenting": {
        "name": "אבי",
        "gender": "male",
        "age": 38,
        "occupation": "מנהל צוות בהייטק",
        "topic": "הורות",
        "issue": "קושי להציב גבולות לילדים, מרגיש שהוא מוותר כדי לא ליצור עימות",
        "event": "אתמול בערב הבן בן ה-9 סירב לעשות שיעורי בית ואבי ויתר אחרי 30 שניות כי לא רצה שתהיה צרחנות",
        "emotional_style": "moderate",  # moderate, expressive, reserved, resistant
        "communication_style": "cooperative",  # cooperative, terse, deflective, verbose
        "background": "אב לשלושה ילדים, אשתו רותי בדרך כלל מטפלת בגבולות. הוא מרגיש שהוא 'האבא הטוב' אבל יודע שזה לא עוזר לילדים.",
        "inner_world": "מפחד מכעס, גדל עם אבא שצעק הרבה, לא רוצה לחזור על זה. מרגיש אשמה כשהוא תקיף.",
    },
    "relationships": {
        "name": "מיכל",
        "gender": "female",
        "age": 33,
        "occupation": "עורכת דין",
        "topic": "זוגיות",
        "issue": "מרגישה שבן הזוג לא רואה אותה, שהיא תמיד מתפשרת",
        "event": "ביום שישי הזמינה ארוחת ערב רומנטית והוא ביטל ברגע האחרון כי חבר הזמין אותו לכדורגל",
        "emotional_style": "expressive",
        "communication_style": "verbose",
        "background": "בזוגיות 5 שנים עם דני. היא מאוד מצליחה בעבודה אבל בבית מרגישה קטנה. מתביישת לבקש.",
        "inner_world": "גדלה בבית שבו למדה ש'בנות חזקות לא מתלוננות'. מפחדת שאם תבקש יותר מדי היא תאבד אותו.",
    },
    "career": {
        "name": "יוסי",
        "gender": "male",
        "age": 45,
        "occupation": "רואה חשבון",
        "topic": "קריירה",
        "issue": "מרגיש תקוע בעבודה, לא מתקדם, מפחד לעשות שינוי",
        "event": "בישיבת צוות השבוע הבוס נתן קידום לקולגה צעיר ויוסי לא אמר מילה למרות שהובטח לו",
        "emotional_style": "reserved",
        "communication_style": "terse",
        "background": "עובד באותו משרד 15 שנה. אשתו לוחצת שיעזוב. הוא מפחד מהלא-נודע.",
        "inner_world": "מאמין שביטחון תעסוקתי הוא הדבר הכי חשוב. אביו פוטר ומעולם לא התאושש. מפחד לחזור על זה.",
    },
    "wellbeing": {
        "name": "נועה",
        "gender": "female",
        "age": 28,
        "occupation": "מעצבת גרפית פרילנסרית",
        "topic": "רווחה רגשית",
        "issue": "לחץ כרוני, חרדות, קושי לומר לא ללקוחות",
        "event": "אתמול לקוח התקשר ב-11 בלילה עם שינויים דחופים והיא ישבה לעבוד במקום ללכת לישון",
        "emotional_style": "expressive",
        "communication_style": "cooperative",
        "background": "עובדת מהבית, גרה לבד. יש לה הרבה לקוחות אבל גבולות מטושטשים. חברות אומרות לה שהיא שורפת את עצמה.",
        "inner_world": "מפחדת שאם תסרב ללקוח הוא יעזוב. ערך עצמי קשור לתפוקה. מתביישת לבקש מחירים גבוהים.",
    },
    "personal_growth": {
        "name": "דוד",
        "gender": "male",
        "age": 52,
        "occupation": "מורה לתנ\"ך",
        "topic": "צמיחה אישית",
        "issue": "מרגיש שהחיים עוברים ועדיין לא מימש את מה שרצה",
        "event": "בשיעור השבוע תלמיד שאל אותו 'למה אתה לא כותב ספר?' והוא נשאר בלי מילים",
        "emotional_style": "moderate",
        "communication_style": "verbose",
        "background": "מלמד 25 שנה, חלם לכתוב ספר על פרשנות מודרנית לתנ\"ך. אף פעם לא התחיל. אשתו מעודדת אבל הוא דוחה.",
        "inner_world": "מפחד שהספר לא יהיה מספיק טוב. מרגיש שהזמן עבר. משווה את עצמו לקולגות שכבר פרסמו.",
    },
    "goals": {
        "name": "שירה",
        "gender": "female",
        "age": 30,
        "occupation": "מנהלת שיווק",
        "topic": "השגת יעדים",
        "issue": "מתחילה פרויקטים ולא מסיימת, תמיד עוברת לדבר הבא",
        "event": "השבוע הבינה שנרשמה לקורס שלישי במקביל בלי לסיים אף אחד מהקודמים, והחברה שלה אמרה לה 'שירה, את בורחת שוב'",
        "emotional_style": "expressive",
        "communication_style": "deflective",
        "background": "מאוד מוכשרת אבל מפוזרת. מרגישה שהיא מאכזבת את עצמה. בקריירה היא מצליחה כי יש מסגרת, אבל בחיים האישיים - כאוס.",
        "inner_world": "מפחדת מכישלון ולכן מעדיפה לעבור לדבר חדש לפני שניתן לשפוט. רואה התחלות כהצלחות ומתעלמת מהחוסר-סיום.",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# USER SIMULATOR LLM
# ══════════════════════════════════════════════════════════════════════════════

def build_simulator_system_prompt(persona: Dict[str, Any]) -> str:
    """Build the system prompt for the user-simulator LLM."""

    gender_word = "גבר" if persona["gender"] == "male" else "אישה"

    style_instructions = {
        "cooperative": "אתה משתף פעולה עם המאמן, עונה על שאלות, ומשתדל לחשוב ולענות בכנות.",
        "terse": "אתה מדבר בקצרה. תשובות של 1-2 משפטים. לא מפרט יותר מדי אלא אם לוחצים.",
        "deflective": "לפעמים אתה מסיט את הנושא, עושה בדיחות, או עונה בצורה כללית. צריך שהמאמן יעזור לך להתמקד.",
        "verbose": "אתה מדבר הרבה, מפרט, מספר סיפורים, לפעמים מתפזר. המאמן צריך לעזור לך למקד.",
    }

    emotional_instructions = {
        "moderate": "הרגשות שלך מתונים - לא דרמטי אבל גם לא קר. מביע רגשות בצורה מאוזנת.",
        "expressive": "אתה רגשי ומביע את מה שאתה מרגיש בגלוי. לפעמים מתרגש או מתרכך.",
        "reserved": "אתה מאופק, קשה לך לדבר על רגשות. עונה יותר בעובדות. צריך עידוד כדי להיפתח.",
        "resistant": "אתה קצת ספקן לגבי התהליך, שואל שאלות, לא תמיד מקבל את מה שהמאמן אומר.",
    }

    return f"""אתה משחק תפקיד של מתאמן (coachee) בשיחת אימון אישי בעברית.

## הפרופיל שלך
- שם: {persona['name']}
- {gender_word}, בן/בת {persona['age']}
- עיסוק: {persona['occupation']}
- נושא האימון: {persona['topic']}
- מה מטריד אותך: {persona['issue']}
- אירוע ספציפי אחרון: {persona['event']}
- רקע: {persona['background']}
- עולם פנימי (מה שלא תגיד מיד, רק אם יחקרו): {persona['inner_world']}

## איך אתה מדבר
{style_instructions[persona['communication_style']]}

## איך אתה מרגיש
{emotional_instructions[persona['emotional_style']]}

## כללים קריטיים
1. ענה רק כ-{persona['name']}. אל תצא מהתפקיד.
2. דבר בעברית טבעית ויומיומית. לא ספרותית.
3. אל תכתוב יותר מ-3 משפטים בדרך כלל (אלא אם הסגנון שלך verbose).
4. אם המאמן שואל על רגשות — תן רגשות אמיתיים מהפרופיל, אבל לא בבת אחת. תן 1-2 רגשות ותן למאמן לחפור.
5. אם המאמן שואל על מחשבה פנימית — תן אותה בשפה פשוטה, כמו שאדם אמיתי חושב.
6. אם המאמן שואל שאלה בינארית (כן/לא) — תענה ישירות.
7. אם המאמן מבקש אירוע ספציפי — ספר על האירוע מהפרופיל, עם פרטים קונקרטיים.
8. אם המאמן שואל על דפוס חוזר — תן 2-3 דוגמאות מתחומי חיים שונים שמתקשרות לפרופיל.
9. אם המאמן מציע תובנה — אל תסכים מיד, אלא תחשוב רגע ואז הגב בכנות.
10. אל תספר הכל מההתחלה. תן למאמן לגלות את הסיפור שלך בהדרגה.
11. התשובה הראשונה שלך כשנשאל אם אתה מוכן — "כן" פשוט.
12. כשמוצגים בפניך ערכים/כוחות — הגב בכנות, אשר או תקן.
13. כשמבקשים ממך לבחור עמדה חדשה או חזון — היה כנה ומעשי, לא פתטי.

## מה לא לעשות
- אל תנתח את עצמך כמו פסיכולוג
- אל תשתמש במונחים מקצועיים (דפוס, פרדיגמה, קוגניטיבי)
- אל תגיד "אני מבין שזה דפוס" — אלא תגיד "כן, אני מכיר את זה" או "זה קורה לי הרבה"
- אל תוסיף הוראות/הערות מטא — רק תגובת מתאמן טהורה"""


async def simulate_user_response(
    coach_message: str,
    conversation_history: List[Dict[str, str]],
    persona: Dict[str, Any],
    current_step: str,
) -> str:
    """Call the LLM to generate a simulated user response."""

    system_prompt = build_simulator_system_prompt(persona)

    # Build message history for the simulator
    messages = [{"role": "system", "content": system_prompt}]

    for msg in conversation_history:
        if msg["sender"] == "coach":
            messages.append({"role": "assistant", "content": f"[מאמן]: {msg['content']}"})
        else:
            messages.append({"role": "user", "content": msg["content"]})

    # Current coach message to respond to
    messages.append({"role": "user", "content": f"[מאמן]: {coach_message}\n\nענה כ-{persona['name']}:"})

    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
    llm = _build_azure_llm(deployment=deployment, temperature=0.7)

    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    lc_messages = []
    for m in messages:
        if m["role"] == "system":
            lc_messages.append(SystemMessage(content=m["content"]))
        elif m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))

    response = await llm.ainvoke(lc_messages)
    text = response.content.strip()

    # Clean up: remove role prefix if the model added one
    for prefix in [f"{persona['name']}:", f"[{persona['name']}]:", "[מתאמן]:", "מתאמן:"]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()

    return text


# ══════════════════════════════════════════════════════════════════════════════
# SIMULATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class SimulationMetrics:
    """Track metrics during a simulation run."""

    def __init__(self, persona_key: str):
        self.persona_key = persona_key
        self.start_time = time.time()
        self.turns: List[Dict[str, Any]] = []
        self.stage_transitions: List[Tuple[str, str, int]] = []  # (from, to, turn)
        self.turns_per_stage: Dict[str, int] = {}
        self.final_step: str = "S0"
        self.final_collected_data: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.stuck_stages: List[Tuple[str, int]] = []  # (stage, turns_stuck)

    def record_turn(self, turn_num: int, user_msg: str, coach_msg: str,
                    step: str, saturation: float, prev_step: str):
        self.turns.append({
            "turn": turn_num,
            "user": user_msg,
            "coach": coach_msg,
            "step": step,
            "saturation": saturation,
        })
        self.turns_per_stage[step] = self.turns_per_stage.get(step, 0) + 1

        if step != prev_step:
            self.stage_transitions.append((prev_step, step, turn_num))

    def finalize(self, state: Dict[str, Any]):
        self.final_step = state.get("current_step", "?")
        self.final_collected_data = state.get("collected_data", {})
        self.duration = time.time() - self.start_time

    def data_completeness(self) -> Dict[str, bool]:
        """Check which collected_data fields are filled."""
        result = {}
        for field in COLLECTED_DATA_FIELDS:
            val = self.final_collected_data.get(field)
            if isinstance(val, list):
                result[field] = len(val) > 0
            elif isinstance(val, dict):
                result[field] = any(v for v in val.values() if v)
            else:
                result[field] = val is not None and str(val).strip() != ""
        return result

    def detect_stuck(self, threshold: int = 8) -> List[Tuple[str, int]]:
        """Detect stages where the coach got stuck (too many turns)."""
        stuck = []
        for stage, count in self.turns_per_stage.items():
            if count >= threshold:
                stuck.append((stage, count))
        self.stuck_stages = stuck
        return stuck


def print_turn(turn_num: int, user_msg: str, coach_msg: str,
               step: str, prev_step: str, saturation: float):
    """Pretty-print a simulation turn."""
    transition = f" ← {prev_step}" if step != prev_step else ""
    stage_name = STAGE_NAMES_HE.get(step, "?")

    print(f"\n{DIM}{'─'*70}{RESET}")
    print(f"{BOLD}תור {turn_num}{RESET}  │  {MAGENTA}{step} {stage_name}{transition}{RESET}  │  רוויה: {saturation:.2f}")
    print(f"{CYAN}👤 מתאמן:{RESET} {user_msg}")
    print(f"{GREEN}🤖 מאמן:{RESET}  {coach_msg[:200]}{'...' if len(coach_msg) > 200 else ''}")


async def run_simulation(
    persona_key: str,
    max_turns: int = 60,
    verbose: bool = True,
) -> SimulationMetrics:
    """Run a full LLM-vs-LLM coaching simulation for one persona."""

    persona = PERSONAS[persona_key]
    metrics = SimulationMetrics(persona_key)

    if verbose:
        print(f"\n{'═'*70}")
        print(f"{BOLD}🧪 סימולציה: {persona['name']} ({persona['topic']}){RESET}")
        print(f"{DIM}   {persona['issue']}{RESET}")
        print(f"{'═'*70}")

    # Initialize state
    state = create_initial_state(
        conversation_id=f"sim_{persona_key}_{int(time.time())}",
        user_id=f"sim_user_{persona_key}",
        language="he",
    )

    conversation_history: List[Dict[str, str]] = []
    prev_step = "S0"
    consecutive_same_stage = 0
    max_same_stage = 10
    nudge_at = 7  # after this many turns in same stage, user says "let's move on"

    for turn_num in range(1, max_turns + 1):
        step_before = state.get("current_step", "S0")

        # ── Generate user message ────────────────────────────────────────
        if turn_num == 1:
            user_msg = "כן"
        elif consecutive_same_stage == nudge_at:
            # User naturally pushes to move on when coach loops too long
            user_msg = "כן, אני מרגיש שסיכמנו את זה — בוא נמשיך הלאה"
        elif consecutive_same_stage >= max_same_stage:
            user_msg = "עניתי הכי טוב שהצלחתי, בוא נתקדם"
        else:
            try:
                user_msg = await simulate_user_response(
                    coach_message=conversation_history[-1]["content"] if conversation_history else "",
                    conversation_history=conversation_history,
                    persona=persona,
                    current_step=step_before,
                )
            except Exception as e:
                metrics.errors.append(f"Turn {turn_num} simulator error: {e}")
                if verbose:
                    print(f"{RED}❌ שגיאת סימולטור בתור {turn_num}: {e}{RESET}")
                break

        # ── Coach processes the message ──────────────────────────────────
        try:
            coach_msg, state = await handle_conversation(
                user_message=user_msg,
                state=state,
                language="he",
                user_gender=persona["gender"],
            )
        except Exception as e:
            metrics.errors.append(f"Turn {turn_num} coach error: {e}")
            if verbose:
                print(f"{RED}❌ שגיאת מאמן בתור {turn_num}: {e}{RESET}")
            break

        step_after = state.get("current_step", "S0")
        saturation = float(state.get("saturation_score", 0))

        # ── Macro-stage transition handling ──────────────────────────────
        # In the real app, when the LLM signals stage_ready_to_complete,
        # the frontend shows a summary card, fetches intro questions for the
        # next macro-stage, and then advances current_step. We replicate
        # that here by detecting the signal and auto-advancing.
        last_msg = state.get("messages", [{}])[-1] if state.get("messages") else {}
        last_internal = last_msg.get("internal_state") or {}
        if last_internal.get("stage_ready_to_complete"):
            current_macro = step_to_macro_stage(step_after)
            if current_macro:
                end_step = MACRO_STAGE_END_STEPS.get(current_macro)
                step_num = int(step_after.replace("S", ""))
                end_num = int(end_step.replace("S", "")) if end_step else -1
                if step_num >= end_num:
                    next_macro = next_macro_stage(current_macro)
                    if next_macro:
                        next_start = MACRO_STAGE_START_STEPS.get(next_macro, step_after)
                        if verbose:
                            print(f"\n{YELLOW}🔄 מעבר קומה: {current_macro} → {next_macro} (S{step_num} → {next_start}){RESET}")
                        state["current_step"] = next_start
                        state["saturation_score"] = 0.0
                        # Simulate "continue coaching" intent
                        apply_station_intent(state, "continue_coaching")
                        step_after = next_start

        # ── Handle trait_picker tool (S12 KaMaZ forces UI) ────────────────
        # In the real app, offer_trait_picker triggers an interactive form.
        # In simulation, auto-fill forces from collected_data if the model
        # signaled it. This unblocks the 6+6 gate.
        cd = last_internal.get("collected_data") or {}
        if isinstance(cd, dict) and (cd.get("offer_trait_picker") or (cd.get("forces") or {}).get("source")):
            forces = state.get("collected_data", {}).get("forces", {})
            src = forces.get("source", [])
            nat = forces.get("nature", [])
            if step_after == "S12" and (len(src) >= 3 or len(nat) >= 1):
                state.setdefault("trait_picker_tool_sent", True)

        # ── Also handle station checkpoints (continue immediately) ───────
        # Station checkpoints can fire at S7+ entries. In sim, auto-continue.
        if state.get("active_shehiya") and not state.get("session_flow", {}).get("continued_immediately_next"):
            apply_station_intent(state, "continue_coaching")

        # ── Track history ────────────────────────────────────────────────
        conversation_history.append({"sender": "user", "content": user_msg})
        conversation_history.append({"sender": "coach", "content": str(coach_msg)})

        metrics.record_turn(turn_num, user_msg, str(coach_msg),
                           step_after, saturation, step_before)

        if verbose:
            print_turn(turn_num, user_msg, str(coach_msg),
                      step_after, step_before, saturation)

        # ── Stuck detection ──────────────────────────────────────────────
        if step_after == prev_step:
            consecutive_same_stage += 1
        else:
            consecutive_same_stage = 0

        if consecutive_same_stage == max_same_stage:
            if verbose:
                print(f"\n{YELLOW}⚠️  תקוע בשלב {step_after} כבר {consecutive_same_stage} תורות{RESET}")
            metrics.errors.append(f"Stuck at {step_after} for {consecutive_same_stage} turns")

        # Force-advance after max_same_stage + 2: skip to next step
        if consecutive_same_stage >= max_same_stage + 2:
            step_progression = {
                "S0": "S1", "S1": "S2", "S2": "S3", "S3": "S4",
                "S4": "S5", "S5": "S6", "S6": "S7", "S7": "S8",
                "S8": "S9", "S9": "S10", "S10": "S11", "S11": "S12",
                "S12": "S13", "S13": "S14", "S14": "S15",
            }
            forced_next = step_progression.get(step_after)
            if forced_next:
                if verbose:
                    print(f"{RED}🔧 דילוג כפוי: {step_after} → {forced_next} (אחרי {consecutive_same_stage} תורות){RESET}")
                metrics.errors.append(f"Force-advanced {step_after} → {forced_next}")
                state["current_step"] = forced_next
                state["saturation_score"] = 0.3
                step_after = forced_next
                consecutive_same_stage = 0

        prev_step = step_after

        # ── Check if session complete ────────────────────────────────────
        if step_after == "S15" and saturation >= 0.7:
            if verbose:
                print(f"\n{GREEN}✅ השיחה הושלמה! שלב סופי: {step_after}{RESET}")
            break

    metrics.finalize(state)
    return metrics


# ══════════════════════════════════════════════════════════════════════════════
# EVALUATION & REPORTING
# ══════════════════════════════════════════════════════════════════════════════

def print_report(metrics: SimulationMetrics):
    """Print a comprehensive evaluation report for a simulation."""
    persona = PERSONAS[metrics.persona_key]

    print(f"\n{'━'*70}")
    print(f"{BOLD}📊 דוח הערכה: {persona['name']} ({persona['topic']}){RESET}")
    print(f"{'━'*70}")

    # Summary
    print(f"\n{BOLD}סיכום כללי:{RESET}")
    print(f"  סה\"כ תורות:    {len(metrics.turns)}")
    print(f"  שלב סופי:      {metrics.final_step} ({STAGE_NAMES_HE.get(metrics.final_step, '?')})")
    print(f"  זמן:           {metrics.duration:.1f}s")
    print(f"  מעברי שלב:     {len(metrics.stage_transitions)}")

    # Stage progression
    print(f"\n{BOLD}התקדמות שלבים:{RESET}")
    reached_idx = ALL_STAGES.index(metrics.final_step) if metrics.final_step in ALL_STAGES else -1
    for i, stage in enumerate(ALL_STAGES):
        name = STAGE_NAMES_HE.get(stage, "")
        turns = metrics.turns_per_stage.get(stage, 0)
        if i <= reached_idx:
            marker = f"{GREEN}✓{RESET}" if turns > 0 else f"{YELLOW}↷{RESET}"
            print(f"  {marker} {stage:4s} {name:12s}  │ {turns} תורות")
        else:
            print(f"  {DIM}○ {stage:4s} {name:12s}  │ ---{RESET}")

    # Turns per stage distribution
    print(f"\n{BOLD}תורות לכל שלב:{RESET}")
    max_bar = 30
    max_turns = max(metrics.turns_per_stage.values()) if metrics.turns_per_stage else 1
    for stage in ALL_STAGES:
        count = metrics.turns_per_stage.get(stage, 0)
        if count == 0:
            continue
        bar_len = int((count / max_turns) * max_bar)
        bar = "█" * bar_len
        color = RED if count >= 8 else YELLOW if count >= 5 else GREEN
        print(f"  {stage:4s} │ {color}{bar} {count}{RESET}")

    # Collected data completeness
    print(f"\n{BOLD}שלמות נתונים שנאספו:{RESET}")
    completeness = metrics.data_completeness()
    filled = sum(1 for v in completeness.values() if v)
    total = len(completeness)
    print(f"  {filled}/{total} שדות מלאים ({filled/total*100:.0f}%)")
    for field, is_filled in completeness.items():
        marker = f"{GREEN}✓{RESET}" if is_filled else f"{RED}✗{RESET}"
        value = metrics.final_collected_data.get(field, None)
        if is_filled and value:
            preview = str(value)[:50]
            print(f"  {marker} {field:20s} │ {preview}")
        else:
            print(f"  {marker} {field:20s} │ ---")

    # Stuck stages
    stuck = metrics.detect_stuck()
    if stuck:
        print(f"\n{YELLOW}{BOLD}⚠️  שלבים תקועים (≥8 תורות):{RESET}")
        for stage, count in stuck:
            print(f"  {RED}• {stage} ({STAGE_NAMES_HE.get(stage, '')}) — {count} תורות{RESET}")

    # Errors
    if metrics.errors:
        print(f"\n{RED}{BOLD}❌ שגיאות:{RESET}")
        for err in metrics.errors:
            print(f"  • {err}")

    # Grade
    print(f"\n{BOLD}ציון:{RESET}")
    score = 0
    score += min(reached_idx / len(ALL_STAGES) * 40, 40)  # Stage progression (40pts)
    score += (filled / total) * 30                          # Data completeness (30pts)
    score += max(0, 20 - len(stuck) * 10)                  # No stuck (20pts)
    score += max(0, 10 - len(metrics.errors) * 5)           # No errors (10pts)
    color = GREEN if score >= 70 else YELLOW if score >= 50 else RED
    print(f"  {color}{BOLD}{score:.0f}/100{RESET}")

    print(f"{'━'*70}\n")
    return score


def save_simulation_log(metrics: SimulationMetrics, output_dir: Path):
    """Save the full simulation transcript to a JSON file."""
    persona = PERSONAS[metrics.persona_key]
    filename = f"sim_{metrics.persona_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = output_dir / filename

    log = {
        "persona": {
            "key": metrics.persona_key,
            "name": persona["name"],
            "topic": persona["topic"],
            "issue": persona["issue"],
        },
        "summary": {
            "total_turns": len(metrics.turns),
            "final_step": metrics.final_step,
            "duration_seconds": metrics.duration,
            "stage_transitions": metrics.stage_transitions,
            "turns_per_stage": metrics.turns_per_stage,
            "data_completeness": metrics.data_completeness(),
            "stuck_stages": metrics.stuck_stages,
            "errors": metrics.errors,
        },
        "collected_data": metrics.final_collected_data,
        "transcript": metrics.turns,
    }

    filepath.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{DIM}📝 לוג נשמר: {filepath}{RESET}")
    return filepath


# ══════════════════════════════════════════════════════════════════════════════
# MULTI-SIMULATION SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

def print_summary(all_metrics: Dict[str, SimulationMetrics]):
    """Print a summary comparing all simulation runs."""
    print(f"\n{'═'*70}")
    print(f"{BOLD}📋 סיכום כל הסימולציות{RESET}")
    print(f"{'═'*70}")

    header = f"{'פרסונה':<12} │ {'נושא':<14} │ {'שלב סופי':<10} │ {'תורות':>6} │ {'נתונים':>7} │ {'תקוע':>5} │ {'ציון':>5}"
    print(f"\n{BOLD}{header}{RESET}")
    print("─" * 75)

    scores = []
    for key, m in all_metrics.items():
        persona = PERSONAS[key]
        completeness = m.data_completeness()
        filled = sum(1 for v in completeness.values() if v)
        total = len(completeness)
        stuck = len(m.detect_stuck())

        reached_idx = ALL_STAGES.index(m.final_step) if m.final_step in ALL_STAGES else -1
        score = 0
        score += min(reached_idx / len(ALL_STAGES) * 40, 40)
        score += (filled / total) * 30
        score += max(0, 20 - stuck * 10)
        score += max(0, 10 - len(m.errors) * 5)
        scores.append(score)

        color = GREEN if score >= 70 else YELLOW if score >= 50 else RED
        step_display = f"{m.final_step} {STAGE_NAMES_HE.get(m.final_step, '')}"
        print(f"{persona['name']:<12} │ {persona['topic']:<14} │ {step_display:<10} │ {len(m.turns):>6} │ {filled}/{total:>4} │ {stuck:>5} │ {color}{score:>4.0f}{RESET}")

    avg_score = sum(scores) / len(scores) if scores else 0
    print("─" * 75)
    color = GREEN if avg_score >= 70 else YELLOW if avg_score >= 50 else RED
    print(f"{BOLD}{'ממוצע':>61} │ {color}{avg_score:>4.0f}{RESET}")
    print(f"{'═'*70}\n")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(description="LLM-vs-LLM BSD Coaching Simulation")
    parser.add_argument("--persona", type=str, help="Run a specific persona (key name)")
    parser.add_argument("--list", action="store_true", help="List available personas")
    parser.add_argument("--max-turns", type=int, default=60, help="Max turns per simulation")
    parser.add_argument("--quiet", action="store_true", help="Minimal output (no per-turn display)")
    parser.add_argument("--no-save", action="store_true", help="Don't save transcript logs")
    args = parser.parse_args()

    if args.list:
        print(f"\n{BOLD}פרסונות זמינות:{RESET}\n")
        for key, p in PERSONAS.items():
            print(f"  {CYAN}{key:<18}{RESET} │ {p['name']} ({p['age']}) │ {p['topic']} │ {p['issue'][:40]}")
        print()
        return

    output_dir = Path(__file__).parent / "simulation_logs"
    if not args.no_save:
        output_dir.mkdir(exist_ok=True)

    personas_to_run = [args.persona] if args.persona else list(PERSONAS.keys())

    # Validate
    for key in personas_to_run:
        if key not in PERSONAS:
            print(f"{RED}❌ פרסונה לא קיימת: {key}{RESET}")
            print(f"   פרסונות זמינות: {', '.join(PERSONAS.keys())}")
            return

    all_metrics: Dict[str, SimulationMetrics] = {}

    for key in personas_to_run:
        metrics = await run_simulation(
            persona_key=key,
            max_turns=args.max_turns,
            verbose=not args.quiet,
        )
        all_metrics[key] = metrics

        print_report(metrics)

        if not args.no_save:
            save_simulation_log(metrics, output_dir)

    if len(all_metrics) > 1:
        print_summary(all_metrics)


if __name__ == "__main__":
    asyncio.run(main())
