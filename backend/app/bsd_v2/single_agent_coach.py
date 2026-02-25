"""
BSD V2 - Single-Agent Conversational Coach

Based on Beni Gal's methodology with emphasis on Shehiya (staying power)
and Clean Language principles.

Unlike V1's multi-layer architecture (router → reasoner → coach → talker),
V2 uses a single LLM call with rich context and clear guidance.
"""

import json
import logging
import asyncio
import time
import os
import re
from typing import Dict, Any, Tuple, Optional, List
from langchain_core.messages import SystemMessage, HumanMessage

from ..bsd.llm import get_azure_chat_llm
from .state_schema_v2 import add_message, get_conversation_history
from .prompt_compact import SYSTEM_PROMPT_COMPACT_HE, SYSTEM_PROMPT_COMPACT_EN
from .prompts.prompt_manager import assemble_system_prompt
from .response_schema import CoachResponseSchema

logger = logging.getLogger(__name__)

# Debug logging: BSD_DEBUG=1 enables extra verbose logs (full messages)
BSD_DEBUG = os.getenv("BSD_DEBUG", "0").strip() in ("1", "true", "yes")
# Temporary: set BSD_V2_SAFETY_NET_DISABLED=1 to bypass all Safety Net logic
SAFETY_NET_DISABLED = os.getenv("BSD_V2_SAFETY_NET_DISABLED", "0").strip() in ("1", "true", "yes")
# A/B test: USE_GEMINI=1 uses Google Gemini instead of Azure OpenAI (optimized for coaching)
USE_GEMINI = os.getenv("USE_GEMINI", "0").strip() in ("1", "true", "yes")


def _bsd_log(tag: str, **kwargs: Any) -> None:
    """Structured log for debugging repetition and stage transitions. Always on."""
    parts = [f"[BSD] {tag}"]
    for k, v in kwargs.items():
        if isinstance(v, str) and len(v) > 120 and not BSD_DEBUG:
            v = v[:117] + "..."
        parts.append(f"{k}={v}")
    logger.info(" | ".join(str(p) for p in parts))


STAGE_EXAMPLES_HE = {
    "S1": [
        {"tags": ["זוגיות", "חיבור"], "text": "משתמש: על הזוגיות שלי | מאמן: מה בזוגיות מעסיק אותך במיוחד?"},
        {"tags": ["מנהיגות", "עבודה"], "text": "משתמש: להיות מנהיג | מאמן: למה אתה מתכוון כשאתה אומר 'להיות מנהיג'?"},
        {"tags": ["לחץ", "שקט"], "text": "משתמש: על השקט הנפשי | מאמן: ספר לי יותר - איפה זה פוגש אותך?"}
    ],
    "S2": [
        {"tags": ["אירוע", "משפחה"], "text": "מאמן: ספר על אירוע אחד ספציפי לאחרונה עם אנשים אחרים שבו הייתה סערה רגשית."},
        {"tags": ["עבודה", "פגישה"], "text": "מאמן: עם מי זה היה, מתי זה קרה, ומה בדיוק קרה שם?"},
        {"tags": ["פנימי", "מחשבה"], "text": "מאמן: אני שומע מחשבה פנימית. בוא ניקח רגע חיצוני של שיחה/אינטראקציה עם מישהו."},
        {"tags": ["מעבר", "דפוס", "התמודדות", "אותנטי"], "text": "מאמן: לאחר שהגדרת על מה תרצה להתאמן, אנחנו עוברים לשלב שבו נכיר את דרכי ההתמודדות האותנטיות שלך. כדי לעשות זאת, אני אבקש ממך לתאר לי סיטואציה, אירוע מחייך שבו פעלת בדרך הרגילה והטיפוסית שלך. ככל שהאירוע יהיה 'טרי' וחי יותר בזיכרונך, כך נוכל להחיות את כל מה שהתרחש בו ולבצע עבודת אימון טובה, מדויקת ועמוקה יותר. המטרה היא שתהיה מצוי כל כולך בתוך חוויית הסיטואציה, כדי שנוכל לזהות דרכה את אופני ההתמודדות האותנטיים שלך. מה שאנחנו מכנים בשם דפוס."}
    ],
    "S3": [
        {"tags": ["רגש", "מה עוד"], "text": "מאמן: מה הרגשת באותו רגע? ... ומה עוד? ... ומה עוד?"},
        {"tags": ["כעס", "תסכול"], "text": "מאמן: מתוסכל... רגשות בדרך כלל לא באים לבד. מה עוד הרגשת שם?"},
        {"tags": ["עלבון", "רגש"], "text": "מאמן: עלבון... ומה עוד?"}
    ],
    "S4": [
        {"tags": ["מחשבה", "משפט"], "text": "מאמן: מה עבר לך בראש באותו רגע? מה המשפט שאמרת לעצמך?"},
        {"tags": ["אמרתי", "לעצמי"], "text": "מאמן: אם היית שם כתובית פנימית למשפט הזה - מה הייתה הכתובת?"},
        {"tags": ["דיוק", "מילולי"], "text": "מאמן: תן את זה במילים המדויקות שרצו לך בראש."}
    ],
    "S5": [
        {"tags": ["מעשה", "מצוי"], "text": "מאמן: מה עשית בפועל באותו רגע? איך הגבת?"},
        {"tags": ["פעולה"], "text": "מאמן: מה עשית ממש בפועל - לא מה חשבת או הרגשת?"},
    ],
    "S6": [
        {"tags": ["רצוי", "מעשה"], "text": "מאמן: מה היית רוצה לעשות במקום? איך היית רוצה להרגיש? מה לומר לעצמך?"},
        {"tags": ["סיכום", "אישור"], "text": "מאמן: בוא נסכם: באותו רגע [מצוי] והיית רוצה [רצוי]. נכון?"},
    ],
    "S7": [
        {"tags": ["פער", "שם"], "text": "מאמן: איך היית קורא לפער בין מה שעשית לבין מה שרצית?"},
        {"tags": ["ציון", "1-10"], "text": "מאמן: בסולם 1-10, כמה חזק הפער הזה עבורך?"},
        {"tags": ["דיוק"], "text": "מאמן: אם הפער היה מקבל שם קצר של 1-2 מילים, מה השם שלו?"}
    ],
    "S8": [
        {"tags": ["דפוס", "חוזר"], "text": "מאמן: איפה עוד אתה מזהה את אותה תגובה בדיוק?"},
        {"tags": ["דוגמאות", "אישור"], "text": "מאמן: תן לי עוד דוגמה אחת... ועוד אחת. מה חוזר ביניהן?"},
        {"tags": ["ליבה"], "text": "מאמן: המצבים שונים, אבל התגובה דומה - אתה מזהה שזה דפוס שלך?"}
    ],
}

STAGE_EXAMPLES_EN = {
    "S1": [
        {"tags": ["topic"], "text": "Coach: What exactly about this topic do you want to coach on?"},
        {"tags": ["clarify"], "text": "Coach: Tell me more - what do you mean by that?"},
        {"tags": ["focus"], "text": "Coach: What's the specific focus within this general area?"}
    ],
    "S2": [
        {"tags": ["event"], "text": "Coach: Please share one specific recent interpersonal event."},
        {"tags": ["detail"], "text": "Coach: Who was there, when did it happen, and what happened exactly?"},
        {"tags": ["external"], "text": "Coach: Let's move from inner thoughts to an external interaction moment."}
    ],
}


def _normalize_text_for_match(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _get_relevant_examples(stage: str, user_message: str, language: str, limit: int = 3) -> list[str]:
    """
    Small in-memory example KB retrieval (dictionary-based).
    Scores examples by tag overlap with current user message.
    """
    db = STAGE_EXAMPLES_HE if language == "he" else STAGE_EXAMPLES_EN
    pool = db.get(stage, [])
    if not pool:
        return []

    msg = _normalize_text_for_match(user_message)
    scored = []
    for item in pool:
        tags = item.get("tags", [])
        score = sum(1 for t in tags if t.lower() in msg)
        scored.append((score, item["text"]))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [text for _, text in scored[:max(1, limit)]]
    return selected


def _strip_static_examples_from_prompt(prompt: str) -> str:
    """
    Remove bulky static examples/code-fences to keep core BSD instructions.
    We keep rules and stage gates, and inject only relevant dynamic examples per turn.
    """
    lines = prompt.splitlines()
    out = []
    in_code_block = False
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Drop explicit example lines to reduce token load.
        if (
            "דוגמה" in stripped
            or "דוגמא" in stripped
            or stripped.lower().startswith("example")
            or stripped.startswith("✅")
            or stripped.startswith("❌")
        ):
            continue
        out.append(ln)
    return "\n".join(out)


def _build_dynamic_system_prompt(base_prompt: str, stage: str, user_message: str, language: str) -> str:
    """
    Build runtime prompt:
    1) Keep core BSD methodology text.
    2) Inject only the most relevant examples for current stage.
    """
    core = _strip_static_examples_from_prompt(base_prompt)
    k = int(os.getenv("BSD_V2_EXAMPLES_PER_TURN", "3"))
    examples = _get_relevant_examples(stage=stage, user_message=user_message, language=language, limit=k)

    if not examples:
        return core

    if language == "he":
        title = "\n\n# דוגמאות ממוקדות לשלב הנוכחי (נשלפות דינמית)\n"
    else:
        title = "\n\n# Focused examples for current stage (dynamically retrieved)\n"

    example_block = title + "\n".join(f"- {e}" for e in examples)
    return core + example_block


def _get_system_prompt(
    state: Dict[str, Any],
    user_message: str,
    language: str,
    user_gender: Optional[str] = None,
) -> str:
    """
    Select runtime prompt strategy.
    BSD_V2_PROMPT_MODE=markdown -> modular prompt_manager (default)
    BSD_V2_PROMPT_MODE=compact  -> legacy compact prompt + dynamic examples
    """
    current_step = state.get("current_step", "S1")
    prompt_mode = os.getenv("BSD_V2_PROMPT_MODE", "markdown").strip().lower()

    if prompt_mode == "compact":
        base_prompt = SYSTEM_PROMPT_COMPACT_HE if language == "he" else SYSTEM_PROMPT_COMPACT_EN
        prompt = _build_dynamic_system_prompt(
            base_prompt=base_prompt,
            stage=current_step,
            user_message=user_message,
            language=language,
        )
        if user_gender:
            if language == "he":
                prompt += "\n\n**מגדר:** המתאמן/ת היא אישה - פנה ב'את'." if user_gender == "female" else "\n\n**מגדר:** המתאמן/ת הוא גבר - פנה ב'אתה'."
            else:
                prompt += f"\n\n**Gender:** Coachee is {user_gender}."
        logger.info("[PROMPT] Using compact mode")
        return prompt

    logger.info("[PROMPT] Using markdown stage mode")
    return assemble_system_prompt(current_step=current_step, language=language, user_gender=user_gender)


def _sanitize_coach_message(coach_message: str) -> str:
    """Remove model artifacts like role prefixes from user-facing message."""
    if not isinstance(coach_message, str):
        return coach_message
    cleaned = coach_message.strip()
    if cleaned.startswith("מאמן:"):
        cleaned = cleaned.replace("מאמן:", "", 1).strip()
    if cleaned.startswith("Coach:"):
        cleaned = cleaned.replace("Coach:", "", 1).strip()
    return cleaned


async def warm_prompt_cache(language: str = "he", steps: tuple = ("S0", "S1")) -> None:
    """
    Pre-warm Azure prompt cache for new conversations.
    Call when user opens/creates a conversation - before first message.
    Runs minimal LLM requests so the next real request hits cache.
    """
    try:
        from ..bsd.llm import get_azure_chat_llm
        llm = get_azure_chat_llm(purpose="talker")
        cache_key_prefix = os.getenv("AZURE_OPENAI_PROMPT_CACHE_KEY_PREFIX", "bsd_v2_markdown_prompt")
        from .state_schema_v2 import create_initial_state
        from .prompts.prompt_manager import assemble_system_prompt

        async def _warm_one(step: str) -> None:
            state = create_initial_state("warmup", "warmup", language)
            state["current_step"] = step
            state["saturation_score"] = 0.0
            placeholder = "כן" if language == "he" else "yes"
            context = build_conversation_context(state, placeholder, language)
            system_prompt = assemble_system_prompt(step, language)
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=context)]
            cache_key = f"{cache_key_prefix}:main_coach:{language}:{step}"
            _ = await _ainvoke_with_prompt_cache(llm, messages, cache_key=cache_key)
            logger.info(f"[BSD V2] Prompt cache warmed: {cache_key}")

        await asyncio.gather(*[_warm_one(s) for s in steps])
    except Exception as e:
        logger.warning(f"[BSD V2] Prompt cache warm-up failed: {e}")


async def _ainvoke_with_prompt_cache(llm, messages, cache_key: str):
    """
    Invoke Azure OpenAI with prompt_cache_key when supported.
    Falls back automatically for deployments/API versions that reject the param.
    """
    try:
        return await llm.ainvoke(messages, prompt_cache_key=cache_key)
    except Exception as cache_exc:
        err = str(cache_exc).lower()
        unsupported_cache_param = (
            "prompt_cache_key" in err
            or "unrecognized request argument" in err
            or "unknown parameter" in err
            or "additional properties are not allowed" in err
            or "unexpected keyword argument" in err
        )
        if unsupported_cache_param:
            logger.warning(
                "[BSD V2] prompt_cache_key unsupported; retrying without it. error=%s",
                cache_exc,
            )
            return await llm.ainvoke(messages)
        raise


def _safe_get_topic_from_collected(collected_data: Any) -> str:
    """Safely extract topic from collected_data - handles dict, str, or invalid types."""
    if collected_data is None:
        return ""
    if isinstance(collected_data, str):
        return collected_data
    if isinstance(collected_data, dict):
        return collected_data.get("topic") or ""
    return ""


def _safe_collected_dict(collected_data: Any) -> Dict[str, Any]:
    """Return collected_data as dict - handles str/invalid by returning empty dict."""
    if collected_data is None:
        return {}
    if isinstance(collected_data, dict):
        return collected_data
    if isinstance(collected_data, str):
        return {"topic": collected_data}
    return {}


def _infer_step_from_coach_message(coach_message: str, language: str) -> Optional[str]:
    """
    Infer current_step from coach message content when model returns plain text (no JSON).
    Uses same indicators as detect_stage_question_mismatch - if coach asks S2 question, we're in S2.
    """
    if not coach_message or not isinstance(coach_message, str):
        return None
    coach_lower = coach_message.lower()
    if language == "he":
        indicators = [
            ("S2", ["מה קרה", "מתי זה היה", "מי היה שם", "ספר לי על אירוע", "סיפור אחד ספציפי", "עם מי זה היה"]),
            ("S3", ["מה הרגשת", "איזה רגש", "איפה הרגשת", "מה עבר בך", "להתעמק ברגשות"]),
            ("S4", ["מה עבר לך בראש", "מה חשבת", "מה אמרת לעצמך"]),
            ("S5", ["מה עשית", "איך הגבת", "מה עשית בפועל"]),
            ("S6", ["מה היית רוצה", "איך היית רוצה להרגיש", "מה לומר לעצמך"]),
            ("S7", ["איך תקרא לפער", "בסולם", "כמה חזק הפער"]),
            ("S8", ["איפה עוד", "מאיפה עוד", "האם אתה מזהה"]),
            ("S9", ["מה אתה מרוויח", "מה אתה מפסיד", "מה ההפסד"]),
            ("S10", ["איזה ערך", "איזו יכולת", "מה חשוב לך"]),
            ("S11", ["איזו עמדה", "מה אתה בוחר", "איזו בחירה"]),
        ]
    else:
        indicators = [
            ("S2", ["what happened", "when was", "who was there", "specific event", "one time"]),
            ("S3", ["what did you feel", "what emotion", "where did you feel"]),
            ("S4", ["what went through", "what did you think", "what did you tell yourself"]),
            ("S5", ["what did you do", "how did you respond"]),
            ("S6", ["what would you want", "how would you want to feel"]),
            ("S7", ["what would you call", "on a scale", "how strong"]),
            ("S8", ["where else", "do you recognize", "does this happen"]),
            ("S9", ["what do you gain", "what do you lose"]),
            ("S10", ["what value", "what ability", "what's important"]),
            ("S11", ["what stance", "what do you choose"]),
        ]
    for step, phrases in indicators:
        if any(p in coach_lower for p in phrases):
            return step
    return None


def _extract_topic_from_conversation(state: Dict[str, Any], user_message: Optional[str], language: str) -> str:
    """Extract topic from conversation when model doesn't return JSON (collected_data empty)."""
    skip = ("מה שמך", "שלום", "היי", "what's your name", "hello", "hi")
    meta = ("הסביר", "מה חסר", "מה כוונתך", "לא הבנתי", "can you explain", "what do you mean")
    candidates = []
    for msg in reversed(state.get("messages", [])):
        if msg.get("sender") == "user":
            c = (msg.get("content") or "").strip()
            if len(c) >= 10 and not any(s in c.lower() for s in skip) and not any(m in c.lower() for m in meta):
                candidates.append(c[:80])
    if user_message and len(user_message.strip()) >= 10:
        um = user_message.strip()
        if not any(s in um.lower() for s in skip) and not any(m in um.lower() for m in meta):
            candidates.insert(0, um[:80])
    return candidates[0] if candidates else ""


def _parse_json_response(
    response_text: str, state: Dict[str, Any], user_message: Optional[str], language: str
) -> Tuple[str, Dict[str, Any]]:
    """Parse JSON from LLM response (fallback when Structured Output not used)."""
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()

    parsed = None
    trailing_text = ""
    try:
        raw = json.loads(response_text)
        parsed = raw if isinstance(raw, dict) else None
        if parsed is None and isinstance(raw, str):
            parsed = {
                "coach_message": raw,
                "internal_state": {"current_step": state.get("current_step", "S1"), "saturation_score": state.get("saturation_score", 0.3), "reflection": "Parsed as string"}
            }
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for start_idx, ch in enumerate(response_text):
            if ch != "{":
                continue
            try:
                candidate, end_idx = decoder.raw_decode(response_text[start_idx:])
                if isinstance(candidate, dict):
                    parsed = candidate
                    trailing_text = response_text[start_idx + end_idx :].strip().strip('"')
                    break
            except json.JSONDecodeError:
                continue

    if parsed is None and response_text.strip():
        plain = response_text.strip()
        if not plain.startswith("{"):
            # Model returned plain text - infer step from message content so we can progress
            inferred_step = _infer_step_from_coach_message(plain, language) or state.get("current_step", "S1")
            if inferred_step == "S0" and user_message and len(user_message.strip()) >= 2:
                inferred_step = "S1"
            collected = _safe_collected_dict(state.get("collected_data"))
            if not collected.get("topic") and state.get("current_step") in ("S0", "S1"):
                topic = _extract_topic_from_conversation(state, user_message, language)
                if topic:
                    collected["topic"] = topic
            parsed = {
                "coach_message": plain,
                "internal_state": {
                    "current_step": inferred_step,
                    "saturation_score": state.get("saturation_score", 0.3),
                    "reflection": "Synthetic from plain text (inferred step from content)",
                    "collected_data": collected,
                }
            }
    if parsed is None:
        raise json.JSONDecodeError("Could not parse model JSON payload", response_text, 0)

    if isinstance(parsed, str):
        parsed = {"coach_message": parsed, "internal_state": {"current_step": state.get("current_step", "S1"), "saturation_score": state.get("saturation_score", 0.3), "reflection": "Parsed as string"}}

    coach_message = parsed.get("coach_message", "") or parsed.get("response", "") or parsed.get("question", "") or trailing_text
    internal_state = parsed.get("internal_state", {})

    if not internal_state:
        stage = parsed.get("stage", state["current_step"])
        saturation = parsed.get("saturation_score", parsed.get("Saturation Score", state["saturation_score"]))
        internal_state = {"current_step": stage if isinstance(stage, str) else state["current_step"], "saturation_score": float(saturation) if isinstance(saturation, (int, float)) else state["saturation_score"], "reflection": "Parsed legacy metadata payload"}

    if isinstance(coach_message, str) and coach_message.strip().startswith("{"):
        coach_message = trailing_text or ""
    if not coach_message:
        coach_message = get_next_step_question(state.get("current_step", "S1"), language)

    return coach_message, internal_state


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT - Uses prompt_manager (markdown) or prompt_compact (compact)
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# SAFETY NETS - Minimal validation to prevent premature transitions
# ══════════════════════════════════════════════════════════════════════════════

def count_turns_in_step(state: Dict[str, Any], step: str) -> int:
    """
    Count how many coach-user exchanges happened in a specific step.
    
    Returns:
        Number of turns (coach messages) in that step
    """
    count = 0
    for msg in state.get("messages", []):
        is_coach = msg.get("sender") == "coach" or msg.get("role") == "assistant"
        internal = msg.get("internal_state") or msg.get("metadata", {}).get("internal_state", {})
        if is_coach and (internal or {}).get("current_step") == step:
            count += 1
    return count


def detect_stage_question_mismatch(
    coach_message: str, current_step: str, language: str = "he", state: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Detect if coach asked a question from a different stage than current_step.
    This happens when LLM moves forward in content but forgets to update current_step in JSON.
    
    CRITICAL: Do NOT advance S1/S2→S3 when no event - would skip S2 (event) entirely.
    
    Returns:
        The correct stage if mismatch detected, None otherwise
    """
    if language == "he":
        stage_indicators = {
            "S2": ["מה קרה", "מתי זה היה", "מי היה שם", "מי עוד היה"],
            "S3": ["מה הרגשת", "איזה רגש", "איפה הרגשת", "מה עבר בך", "להתעמק ברגשות"],
            "S4": ["מה עבר לך בראש", "מה חשבת", "מה אמרת לעצמך"],
            "S5": ["מה עשית", "איך הגבת", "מה עשית בפועל"],
            "S6": ["מה היית רוצה", "איך היית רוצה להרגיש", "מה לומר לעצמך"],
            "S7": ["איך תקרא לפער", "בסולם", "כמה חזק הפער"],
            "S8": ["איפה עוד", "מאיפה עוד", "האם אתה מזהה", "האם זה קורה"],
            "S9": ["מה אתה מרוויח", "מה אתה מפסיד", "מה ההפסד", "מה הרווח"],
            "S10": ["איזה ערך", "איזו יכולת", "מה חשוב לך"],
            "S11": ["איזו עמדה", "מה אתה בוחר", "איזו בחירה"]
        }
    else:
        stage_indicators = {
            "S2": ["what happened", "when was", "who was there"],
            "S3": ["what did you feel", "what emotion", "where did you feel"],
            "S4": ["what went through", "what did you think", "what did you tell yourself"],
            "S5": ["what did you do", "how did you respond"],
            "S6": ["what would you want", "how would you want to feel"],
            "S7": ["what would you call", "on a scale", "how strong"],
            "S8": ["where else", "do you recognize", "does this happen"],
            "S9": ["what do you gain", "what do you lose"],
            "S10": ["what value", "what ability", "what's important"],
            "S11": ["what stance", "what do you choose"]
        }
    
    coach_lower = coach_message.lower()
    
    # Check each stage's indicators
    for stage, indicators in stage_indicators.items():
        if any(ind in coach_lower for ind in indicators):
            if stage != current_step:
                # CRITICAL: Don't advance S1/S2→S3+ when no event - would skip event collection!
                if current_step in ("S1", "S2") and stage in ("S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11"):
                    if state:
                        has_event, _ = has_sufficient_event_details(state)
                        if not has_event:
                            logger.warning(f"[Stage Mismatch!] Coach asked {stage} but current_step={current_step} and NO EVENT - BLOCKING advance")
                            return None
                logger.error(f"[Stage Mismatch!] Coach asked {stage} question but current_step={current_step}")
                logger.error(f"[Stage Mismatch!] Question: {coach_message[:100]}")
                return stage  # Return the correct stage
    
    return None  # No mismatch detected


def has_clear_topic_for_s2(state: Dict[str, Any], user_message: Optional[str] = None) -> Tuple[bool, str]:
    """
    Minimal safety net: block S1→S2 only in extreme cases.
    Criteria are now in the prompt (s1_topic.md); this is a fallback for edge cases.
    
    IMPORTANT: user_message is the CURRENT turn's message - it's not in state yet when we validate.
    If user gives event in this message (e.g. "לפני יומיים רציתי לתרום... בעלי חשב אחרת"), we must allow.
    
    Returns:
        (has_clear_topic, reason_if_not)
    """
    messages = state.get("messages", [])
    recent_user_msgs = [
        msg.get("content", "").strip()
        for msg in messages[-8:]
        if msg.get("sender") == "user" and msg.get("content", "").strip()
    ]
    
    # ✅ FIX: Include current user message - it's not in state yet during validation!
    if user_message and user_message.strip():
        recent_user_msgs = list(recent_user_msgs)  # copy
        recent_user_msgs.append(user_message.strip())
    
    # ✅ FIX: If current message contains event (מתי, איפה, מי, מה) - allow immediately
    if user_message and len(user_message.strip()) >= 30:
        um_lower = user_message.lower()
        event_indicators_he = ["אתמול", "לפני", "שבוע", "חודש", "בעלי", "אשתי", "בן ", "בת ", "חבר", "קרה", "אמר", "דיברנו", "שיחה"]
        event_indicators_en = ["yesterday", "last week", "husband", "wife", "said", "happened", "told", "talked"]
        if any(p in um_lower for p in event_indicators_he + event_indicators_en):
            return True, ""
    
    # Block only if: 0-1 user messages (extreme case). Trust LLM when 2+
    if len(recent_user_msgs) < 2:
        return False, "need_more_clarification"
    
    # With 2+ messages, trust the prompt/LLM - topic criteria are in s1_topic.md
    return True, ""


def get_s1_explanation_for_missing_info(reason: str, language: str) -> str:
    """
    Generate explanatory response when user is frustrated in S1 but topic is not clear enough.
    
    User asked "what's missing?" - explain WHY we need more clarity.
    """
    if language == "he":
        explanations = {
            "need_more_clarification": (
                "אני מבין את השאלה. אני שואל עוד כי **צריך שהנושא יהיה מוגדר היטב** לפני שנמשיך. "
                "כדי לזהות את הדפוס שלך, אני צריך להבין במדויק על מה אתה רוצה להתאמן. "
                "מה **בדיוק** בנושא הזה מעסיק אותך? במה אתה מרגיש תקוע?"
            ),
            "too_vague": (
                "אני מבין שאתה רוצה להמשיך. אני שואל עוד כי **הנושא עדיין כללי מדי**. "
                "כדי לעזור לך באמת, אני צריך להבין - באיזה **מצבים ספציפיים** או **הקשרים** "
                "הדבר הזה מעסיק אותך במיוחד?"
            ),
            "missing_context": (
                "אני שומע אותך. אני מבקש עוד הבהרה כי **חסר לי הקשר**. "
                "כדי שנוכל לזהות את הדפוס שלך, חשוב שאבין - "
                "**עם מי** או **באיזה סיטואציות** זה מעסיק אותך במיוחד?"
            )
        }
        return explanations.get(reason, explanations["missing_context"])
    else:
        explanations = {
            "need_more_clarification": (
                "I understand you want to continue. "
                "The reason I'm asking for more clarification is that to identify your pattern, "
                "I need to understand exactly what you want to work on. "
                "Tell me - what specifically concerns you about this topic?"
            ),
            "too_vague": (
                "I understand. "
                "To really help you, I need to understand more deeply - "
                "in what situation or context does this concern you?"
            ),
            "missing_context": (
                "I hear you. "
                "To identify your pattern, it's important I understand - "
                "in what situations or with whom does this particularly concern you?"
            )
        }
        return explanations.get(reason, explanations["missing_context"])


def get_next_step_question(current_step: str, language: str = "he") -> str:
    """
    Get appropriate next question based on current step (for loop prevention).
    
    Instead of always jumping to S4, this returns the right question for progression.
    """
    if language == "he":
        step_questions = {
            "S0": "על מה תרצה להתאמן?",
            "S1": "עכשיו כדי שנוכל להבין לעומק, אני מבקש שתשתף אותי בסיפור אחד ספציפי – שיחה או אינטראקציה שהתרחשה לאחרונה, עם אנשים נוספים, שבה הרגשת סערה רגשית. ספר לי: עם מי זה היה? מתי? מה קרה שם?",  # Move to S2!
            "S2": "ספר לי על רגע אחד ספציפי שבו זה קרה - מתי זה היה?",
            "S3": "אני מבין. עכשיו אני רוצה לשמוע - מה עבר לך בראש באותו רגע?",
            "S4": "מה עשית באותו רגע?",
            "S5": "מה עשית בפועל? איך הגבת?",
            "S6": "מה היית רוצה לעשות במקום? איך להרגיש? מה לומר לעצמך?",
            "S7": "איך תקרא לפער הזה? תן לו שם משלך.",
            "S8": "איפה עוד זה קורה?",
            "S9": "מה אתה מרוויח מהדפוס הזה?",
            "S10": "מה חשוב לך בחיים? איזה ערך?",
            "S11": "איזו עמדה חדשה אתה בוחר?",
            "S12": "איפה הבחירה הזו מובילה אותך?",
            "S13": "מה תעשה בפעם הבאה?"
        }
    else:
        step_questions = {
            "S0": "What would you like to work on?",
            "S1": "Tell me about one specific time when this happened - when was it?",  # Move to S2!
            "S2": "Tell me about one specific moment when this happened - when was it?",
            "S3": "I understand. Now I want to hear - what went through your mind in that moment?",
            "S4": "What did you do in that moment?",
            "S5": "What did you actually do? How did you respond?",
            "S6": "What would you have wanted to do instead? How to feel? What to tell yourself?",
            "S7": "What would you call this gap? Give it a name.",
            "S8": "Where else does this happen?",
            "S9": "What do you gain from this pattern?",
            "S10": "What's important to you in life? What value?",
            "S11": "What new stance do you choose?",
            "S12": "Where does this choice lead you?",
            "S13": "What will you do next time?"
        }
    
    return step_questions.get(current_step, "בוא נמשיך הלאה." if language == "he" else "Let's continue.")


def detect_re_asking_for_event(
    coach_message: str,
    state: Dict[str, Any],
    language: str = "he",
    user_message: Optional[str] = None
) -> Optional[Tuple[str, str]]:
    """
    If coach asks for event again but user already gave full event - override with
    the *next valid stage question* (usually S3 from S2).
    Prevents the "ספרתי לך על הרגע במגרש" loop.
    Also runs in S1 when user_message contains event (e.g. "אתמול עם בעלי...").
    """
    current_step = state.get("current_step", "")
    if current_step not in ("S1", "S2", "S3"):
        return None
    coach_lower = coach_message.lower()
    event_asking_phrases = [
        "אירוע ספציפי", "תיקח אותי לרגע", "ספר לי על אירוע",
        "פעם אחת ספציפית", "רגע מסוים שבו", "מתי זה היה", "עם מי זה היה"
    ]
    if not any(p in coach_lower for p in event_asking_phrases):
        return None
    has_event, _ = has_sufficient_event_details(state)
    # S1: user may have given event in current message (not yet in state)
    user_gave_event_in_msg = False
    if current_step == "S1" and user_message and len(user_message.strip()) >= 30:
        um_lower = user_message.lower()
        event_indicators = ["אתמול", "לפני", "שבוע", "חודש", "בעלי", "אשתי", "בן ", "בת ", "חבר", "קרה", "אמר", "דיברנו", "שיחה", "yesterday", "last week", "husband", "wife", "said", "happened"]
        user_gave_event_in_msg = any(p in um_lower for p in event_indicators)
    if not has_event and not user_gave_event_in_msg:
        return None
    current_step = state.get("current_step", "S2")
    logger.warning(f"[Safety Net] Coach re-asking for event but user already gave it - overriding with stage-aware next question")

    if current_step == "S1":
        # User gave event in S1 message - move to S3 (emotions) to avoid re-asking
        if language == "he":
            return ("מצטער על החזרה! שמעתי את האירוע. עכשיו בוא ניכנס פנימה - מה הרגשת באותו רגע?", "S3")
        return ("Sorry for repeating! I heard the event. Now let's go into that moment - what did you feel right then?", "S3")

    if current_step == "S2":
        if language == "he":
            return (
                "מצטער על החזרה! שמעתי את האירוע. עכשיו בוא ניכנס פנימה לרגע הזה - מה הרגשת באותו רגע?",
                "S3",
            )
        return (
            "Sorry for repeating! I heard the event. Now let's go into that moment - what did you feel right then?",
            "S3",
        )

    # If we're already in S3 and still got an event-reask, move to S4 question.
    if language == "he":
        return (
            "מצטער על החזרה! כבר יש לנו את האירוע. עכשיו אני רוצה להבין - מה עבר לך בראש באותו רגע?",
            "S4",
        )
    return (
        "Sorry for repeating! We already have the event. Now I want to understand - what went through your mind in that moment?",
        "S4",
    )


def check_repeated_question(coach_message: str, history: list, current_step: str, language: str = "he", user_message: Optional[str] = None) -> Optional[Tuple[str, Optional[str]]]:
    """
    Check if coach is repeating a question that was already answered or sent recently.
    
    Returns:
        None if no override needed.
        str: correction message only (step unchanged).
        (str, str): (correction message, step_override) when we should advance (e.g. S1→S3).
    """
    # Get recent messages
    recent_coach_messages = [
        msg.get("content", "") for msg in history[-8:]
        if msg.get("sender") in ["coach", "assistant"]
    ]
    
    recent_user_messages = [
        msg.get("content", "").lower() for msg in history[-4:]
        if msg.get("sender") == "user"
    ]
    
    # === CRITICAL: S0/S1/S2 + emotions question without event = wrong! Block immediately ===
    if current_step in ("S0", "S1", "S2"):
        emotions_indicators_he = [
            "מה הרגשת", "איזה רגש", "להתעמק ברגשות", "מה עבר בך", "איפה הרגשת",
            "עכשיו אני רוצה להתעמק ברגשות", "מה הרגשת באותו רגע"  # exact phrases from bug
        ]
        emotions_indicators_en = ["what did you feel", "what emotion", "delve into emotions", "how did you feel"]
        indicators = emotions_indicators_he if language == "he" else emotions_indicators_en
        coach_lower = coach_message.lower()
        if any(ind in coach_lower for ind in indicators):
            _bsd_log("REPETITION_RULE", rule="S1_emotions_question", step=current_step)
            logger.warning(f"[Safety Net] {current_step} but coach asked emotions question - BLOCKING (no event yet!)")
            return (get_next_step_question(current_step, language), None)
    
    if language == "he":
        # === CRITICAL: Check if user said they're done ===
        import re
        
        # Phrases (can appear anywhere)
        completion_phrases = [
            "זה מסכם", "זה הכל", "כל הרגשות", "זה כל הרגשות",
            "די לי", "כבר כתבתי", "אמרתי את כל", "זה מספיק", 
            "סיימתי", "זה מה שיש", "אין יותר", "אין עוד",
            # NEW: From infinite loop bug analysis
            "לא קרה כלום", "לא קרה שום דבר", "לא היה כלום",
            "כתבתי לך", "אמרתי לך", "עניתי כבר", "עניתי על זה",
            "מה עכשיו", "אולי נמשיך", "בוא נמשיך"
        ]
        
        # Short words (need word boundaries)
        completion_words = ["זהו", "די", "מספיק", "הכל"]
        
        user_said_done = any(
            any(phrase in msg for phrase in completion_phrases) or
            any(re.search(rf'\b{word}\b', msg) for word in completion_words)
            for msg in recent_user_messages
        )
        
        # === Check for "מה עוד?" variants (most common loop) ===
        asking_what_else = any(
            pattern in coach_message.lower()
            for pattern in ["מה עוד", "עוד משהו", "מה נוסף"]
        )
        
        # Count how many "מה עוד?" questions in recent history
        what_else_count = sum(
            1 for msg in recent_coach_messages
            if any(pattern in msg for pattern in ["מה עוד", "עוד משהו"])
        )
        
        # S1: If user gave event (in current or recent msg) and coach asks "מה עוד" - progress, don't loop
        event_indicators = ["אתמול", "לפני", "שבוע", "חודש", "בעלי", "אשתי", "בן ", "בת ", "חבר", "קרה", "אמר", "דיברנו", "שיחה"]
        all_user_text = list(recent_user_messages)
        if user_message and user_message.strip():
            all_user_text.append(user_message.strip().lower())
        user_gave_event = any(any(p in t for p in event_indicators) for t in all_user_text if len(t) >= 20)
        if current_step == "S1" and user_gave_event and asking_what_else:
            _bsd_log("REPETITION_RULE", rule="S1_user_gave_event_what_else", step=current_step)
            logger.warning(f"[Safety Net] S1: User gave event, coach asking 'מה עוד?' - progressing to S3")
            msg = "מצטער על החזרה! שמעתי את האירוע. עכשיו בוא ניכנס פנימה - מה הרגשת באותו רגע?" if language == "he" else "Sorry for repeating! I heard the event. Now let's go into that moment - what did you feel right then?"
            return (msg, "S3")  # Advance to S3
        
        # If user said done + coach asking "what else?" again = LOOP!
        if user_said_done and asking_what_else:
            _bsd_log("REPETITION_RULE", rule="user_said_done_but_what_else", step=current_step)
            logger.warning(f"[Safety Net] User said done, but coach asking 'מה עוד?' - BLOCKING")
            return (get_next_step_question(current_step, language), None)
        
        # If "מה עוד?" asked 3+ times = LOOP!
        if what_else_count >= 3:
            _bsd_log("REPETITION_RULE", rule="what_else_3plus", count=what_else_count, step=current_step)
            logger.warning(f"[Safety Net] 'מה עוד?' asked {what_else_count} times - BLOCKING")
            return (get_next_step_question(current_step, language), None)
        
        # === Check if coach is sending the EXACT same message again ===
        if coach_message in recent_coach_messages[-2:]:
            _bsd_log("REPETITION_RULE", rule="exact_repeat", step=current_step)
            logger.warning(f"[Safety Net] Detected EXACT repeated message")
            return (get_next_step_question(current_step, language), None)
        
        # === Generic patterns (S1 loop: "תוכל לספר לי יותר" etc.) ===
        # SKIP override if user asked for clarification - coach's response is explanation, not a loop
        clarification_phrases_he = ["מה כוונה", "מה הכוונה", "לא הבנתי", "להבין", "להסביר", "מה את מתכוונת", "מה אתה מתכוון"]
        user_asked_clarification = user_message and any(
            p in user_message.strip().lower() for p in clarification_phrases_he
        )
        # SKIP override if coach already asks for event - that's progression, not a loop!
        event_asking_he = ["אירוע ספציפי", "ספר לי על אירוע", "פעם אחת ספציפית", "רגע מסוים שבו", "מתי זה היה", "עם מי זה היה"]
        coach_asks_for_event = any(p in coach_message for p in event_asking_he)
        if not user_asked_clarification and not coach_asks_for_event:
            generic_patterns = [
                "ספר לי עוד על הרגע הזה",
                "מה בדיוק קרה",
                "ספר לי יותר על",
                "תוכל לספר לי יותר",
                "תוכל לספר לי יותר על",
                "מה בדיוק ב", "מה בדיוק היית", "מה בדיוק",
                "מה בזה מעסיק", "מה בזה מעסיק אותך",  # S1 drilling loop
                "על איזה היבט", "מה בדיוק היית רוצה",  # S1 drilling variants
            ]
            
            generic_count = sum(
                1 for msg_content in recent_coach_messages
                if any(pattern in msg_content for pattern in generic_patterns)
            )
            
            # S1: trigger after 2 (not 3) - catch loop earlier. Advance to S2 when topic is clear.
            threshold = 2 if current_step == "S1" else 3
            if generic_count >= threshold:
                _bsd_log("REPETITION_RULE", rule="generic_patterns", count=generic_count, threshold=threshold, step=current_step)
                logger.warning(f"[Safety Net] Too many generic questions ({generic_count})")
                # In S1: advance to S2 (ask for event) to break the drilling loop
                step_override = "S2" if current_step == "S1" and len(recent_user_messages) >= 2 else None
                return (get_next_step_question(current_step, language), step_override)
    
    else:  # English
        # Check if user said they're done
        completion_keywords = [
            "that's all", "that's it", "all the", "i'm done",
            "that's everything", "nothing else", "no more",
            # NEW: From infinite loop bug analysis
            "nothing happened", "nothing else happened",
            "i told you", "already told", "already answered",
            "what now", "let's continue", "let's move on"
        ]
        
        user_said_done = any(
            keyword in msg for msg in recent_user_messages
            for keyword in completion_keywords
        )
        
        asking_what_else = any(
            pattern in coach_message.lower()
            for pattern in ["what else", "anything else", "what more"]
        )
        
        what_else_count = sum(
            1 for msg in recent_coach_messages
            if "what else" in msg.lower() or "anything else" in msg.lower()
        )
        
        if user_said_done and asking_what_else:
            logger.warning(f"[Safety Net] User said done, but coach asking 'what else?' - BLOCKING")
            return (get_next_step_question(current_step, language), None)
        
        if what_else_count >= 3:
            logger.warning(f"[Safety Net] 'What else?' asked {what_else_count} times - BLOCKING")
            return (get_next_step_question(current_step, language), None)
        
        if coach_message in recent_coach_messages[-2:]:
            logger.warning(f"[Safety Net] Detected EXACT repeated message")
            return (get_next_step_question(current_step, language), None)
        
        # === Generic patterns (English S1 loop) ===
        # SKIP override if user asked for clarification
        clarification_phrases_en = ["what do you mean", "what do you mean by", "i don't understand", "can you explain", "clarify", "what are you asking"]
        user_asked_clarification = user_message and any(
            p in user_message.strip().lower() for p in clarification_phrases_en
        )
        # SKIP override if coach already asks for event
        event_asking_en = ["specific event", "tell me about a time", "when was it", "who was there", "one specific time"]
        coach_asks_for_event = any(p in coach_message.lower() for p in event_asking_en)
        if not user_asked_clarification and not coach_asks_for_event:
            generic_patterns_en = [
                "tell me more about",
                "can you tell me more",
                "what exactly about",
                "what specifically"
            ]
            generic_count = sum(
                1 for msg_content in recent_coach_messages
                if any(pattern in msg_content.lower() for pattern in generic_patterns_en)
            )
            threshold = 2 if current_step == "S1" else 3
            if generic_count >= threshold:
                logger.warning(f"[Safety Net] Too many generic questions ({generic_count})")
                return (get_next_step_question(current_step, language), None)
    
    return None


async def user_already_gave_emotions_llm(state: Dict[str, Any], llm, language: str = "he") -> bool:
    """
    Use LLM to detect if user already shared emotions (smart detection).
    More accurate than keyword list - detects "רע", "חנוק", "לא טבעי", etc.
    """
    messages = state.get("messages", [])
    recent_user_messages = [
        msg.get("content", "")
        for msg in messages[-6:]
        if msg.get("sender") == "user" and msg.get("content")
    ]
    
    if not recent_user_messages:
        return False
    
    if language == "he":
        prompt = f"""האם במסרים הבאים המשתמש שיתף רגשות?

רגשות = כעס, עצב, שמחה, פחד, קנאה, תסכול, רע, טוב, חנוק, נזהר, חסום, וכו'

מסרים:
{chr(10).join(f"- {msg}" for msg in recent_user_messages)}

ענה רק: כן או לא"""
    else:
        prompt = f"""Did the user share emotions in the following messages?

Emotions = anger, sadness, joy, fear, jealousy, frustration, bad, good, stuck, scared, etc.

Messages:
{chr(10).join(f"- {msg}" for msg in recent_user_messages)}

Answer only: yes or no"""
    
    try:
        detection_messages = [
            SystemMessage(content="You detect emotions in text." if language == "en" else "אתה מזהה רגשות בטקסט."),
            HumanMessage(content=prompt)
        ]
        
        response = await _ainvoke_with_prompt_cache(
            llm,
            detection_messages,
            cache_key=f"{os.getenv('AZURE_OPENAI_PROMPT_CACHE_KEY_PREFIX', 'bsd_v2')}:emotion_detection:{language}",
        )
        answer = response.content.strip().lower()
        
        has_emotions = "כן" in answer or "yes" in answer
        logger.info(f"[Emotion Detection] LLM detected emotions: {has_emotions}")
        return has_emotions
        
    except Exception as e:
        logger.error(f"[Emotion Detection] LLM call failed: {e}")
        # Fallback to simple keyword check
        return user_already_gave_emotions_simple(state)


def user_already_gave_emotions_simple(state: Dict[str, Any], last_turns: int = 3) -> bool:
    """
    Fallback: Simple keyword-based emotion detection.
    Used if LLM detection fails.
    """
    emotion_keywords_he = [
        "קנאה", "כעס", "עצב", "שמחה", "פחד", "תסכול", "אכזבה",
        "גאווה", "בושה", "אשם", "מבוכה", "עלבון", "ניצול",
        # Extended list
        "רע", "טוב", "חנוק", "נזהר", "לא טבעי", "מתוח", "לחוץ",
        "מבולבל", "מופתע", "נעלב", "מוטרד", "דאוג",
        "הרגשתי", "מרגיש"
    ]
    emotion_keywords_en = [
        "jealous", "anger", "sad", "happy", "fear", "frustrat",
        "disappoint", "proud", "shame", "guilt", "embarrass",
        "bad", "good", "stuck", "scared", "nervous", "worried",
        "felt", "feeling"
    ]
    
    messages = state.get("messages", [])
    recent_user_messages = [
        msg.get("content", "").lower() 
        for msg in messages[-last_turns * 2:] 
        if msg.get("sender") == "user" and msg.get("content")
    ]
    
    for msg in recent_user_messages:
        if any(emotion in msg for emotion in emotion_keywords_he):
            return True
        if any(emotion in msg for emotion in emotion_keywords_en):
            return True
    
    return False


def user_already_gave_emotions(state: Dict[str, Any], last_turns: int = 3) -> bool:
    """
    Synchronous wrapper for backwards compatibility.
    Uses simple keyword detection.
    
    For better detection, use user_already_gave_emotions_llm() in async context.
    """
    return user_already_gave_emotions_simple(state, last_turns)


def detect_stuck_loop(state: Dict[str, Any], last_n: int = 4) -> bool:
    """
    Detect if coach is stuck repeating the same question.
    """
    messages = state.get("messages", [])
    recent_coach = [
        msg.get("content", "")
        for msg in messages[-last_n:]
        if msg.get("sender") == "coach" and msg.get("content")
    ]
    
    if len(recent_coach) < 2:
        return False
    
    # Check exact repetition
    if recent_coach[-1] == recent_coach[-2]:
        logger.warning(f"[Loop Detection] Exact repetition detected!")
        return True
    
    # Check similar questions
    key_phrases = ["מה עוד קרה", "מה הרגשת", "what else happened", "what did you feel"]
    for phrase in key_phrases:
        count = sum(1 for msg in recent_coach if phrase in msg)
        if count >= 2:
            logger.warning(f"[Loop Detection] Repeated question detected: '{phrase}' x{count}")
            return True
    
    return False


def count_pattern_examples_in_s7(state: Dict[str, Any]) -> int:
    """
    Count how many pattern examples user gave in S7 (by content, not just turns).
    """
    messages = state.get("messages", [])
    
    # Get user messages (approximate S7 by looking at recent messages)
    user_msgs = [
        msg.get("content", "")
        for msg in messages[-12:]
        if msg.get("sender") == "user" and msg.get("content")
    ]
    
    if not user_msgs:
        return 0
    
    all_text = " ".join(user_msgs)
    example_count = 0
    
    # Method 1: Count explicit example markers
    example_count += all_text.count("למשל")
    example_count += all_text.count("גם")
    example_count += all_text.count("וגם")
    
    # Method 2: Count location/context indicators
    # "עם חברים", "בעבודה", "עם בן הזוג"
    context_patterns = [
        "עם חברים", "עם משפחה", "עם בן הזוג", "עם אישתי", "עם בעלי",
        "בעבודה", "בבית", "במשרד", "בפגישה",
        "with friends", "with family", "at work", "at home"
    ]
    
    for pattern in context_patterns:
        if pattern in all_text:
            example_count += 1
    
    # Method 3: Check if user explicitly said multiple places
    multiple_indicators = [
        "בהרבה מקומות", "בכל מקום", "בהמון", "בכמה",
        "in many places", "everywhere", "in multiple"
    ]
    
    if any(ind in all_text for ind in multiple_indicators):
        example_count += 2  # "many places" = at least 2 examples
    
    logger.info(f"[Pattern Examples] Counted {example_count} examples in S7")
    return example_count


def user_said_already_gave_examples(user_message: str) -> bool:
    """Check if user explicitly said they already gave examples"""
    phrases_he = [
        "אמרתי כבר", "כבר אמרתי", "כבר נתתי",
        "זה מופיע ב", "זה קורה ב",
        "אמרתי לך"
    ]
    phrases_en = [
        "i already said", "already told", "already gave",
        "it happens in", "it occurs in"
    ]
    
    msg_lower = user_message.lower()
    return any(p in msg_lower for p in phrases_he + phrases_en)


async def validate_situation_quality(state: Dict[str, Any], llm, language: str = "he") -> Tuple[bool, Optional[str]]:
    """
    Validate that the situation (S2) meets basic criteria using FAST rule-based checks.
    We rely on the LLM's prompt instructions for detailed validation to avoid double LLM calls.
    
    This function only performs lightweight checks to catch obvious issues.
    
    Returns:
        (is_valid, guidance_message_if_invalid)
    """
    messages = state.get("messages", [])
    
    # Get user messages from S2
    user_msgs_s2 = [
        msg.get("content", "")
        for msg in messages[-20:]
        if msg.get("sender") == "user" and msg.get("content")
    ]
    
    if len(user_msgs_s2) < 2:
        # Not enough data yet
        return True, None
    
    situation_text = "\n".join(user_msgs_s2[-5:])  # Last 5 user messages
    situation_lower = situation_text.lower()
    
    # FAST rule-based checks (no LLM call!)
    
    # Check 1: Basic length (too short = not enough details)
    if len(situation_text) < 50:
        logger.info(f"[Situation Validation] Too short ({len(situation_text)} chars)")
        return True, None  # Let LLM handle it
    
    # Check 2: "I was alone" = no interpersonal arena
    alone_indicators = ["הייתי לבד", "הייתי בבית לבד", "לבד בבית", "i was alone", "by myself", "all alone"]
    if any(ind in situation_lower for ind in alone_indicators):
        logger.info(f"[Situation Validation] Detected 'alone' situation - needs interpersonal")
        if language == "he":
            return False, """אני מבין את החוויה שתיארת. כדי לזהות דפוס אנחנו מחפשים אירוע שהיו מעורבים בו אנשים נוספים מלבדיך.

בוא ננסה משהו אחר - ספר לי על **אירוע מהחיים שלך** (יכול להיות מהעבודה, עם חברים, עם משפחה, בכל מצב) שבו היו אנשים אחרים וחווית סערה רגשית.

**חשוב:** האירוע לא חייב להיות קשור לנושא האימון - הדפוס שלך מתגלה בכל תחומי החיים, ולפעמים דווקא באירוע מתחום אחר לגמרי."""
        else:
            return False, "I understand the experience you described. To identify a pattern we're looking for an event where other people were involved besides you. Let's try something else - tell me about **an event from your life** (can be from work, with friends, with family, any situation) where other people were present and you experienced emotional turmoil. **Important:** The event doesn't have to be related to the coaching topic - your pattern shows up in all areas of life, sometimes most clearly in a completely different area."
    
    # All basic checks passed - let the LLM prompt handle detailed validation
    logger.info(f"[Situation Validation] Basic checks passed (fast mode, no LLM call)")
    return True, None


def user_questions_unrelated_event(user_message: str) -> bool:
    """
    Check if user is asking why the event doesn't have to be related to coaching topic.
    """
    questions_he = [
        "למה לא", "למה אירוע", "למה סיטואציה", "למה דווקא",
        "מה הקשר", "צריך להיות קשור", "לא קשור",
        "אירוע אחר", "אירוע שלא", "למה לא קשור"
    ]
    questions_en = [
        "why not", "why event", "why situation",
        "what's the connection", "needs to be related", "not related",
        "different event", "unrelated event"
    ]
    
    msg_lower = user_message.lower()
    return any(q in msg_lower for q in questions_he + questions_en)


def user_wants_to_continue(user_message: str) -> bool:
    """
    Check if user is signaling they want to move forward.
    Indicators: "already told you", "let's continue", "nothing happened"
    
    NOTE: This is just an INDICATOR. Don't automatically allow transition!
    Check if we have sufficient info first, then explain if not.
    """
    continue_signals = [
        # Hebrew
        "כתבתי לך", "אמרתי לך", "עניתי", "כבר אמרתי",
        "לא קרה כלום", "לא קרה שום דבר", "לא היה",
        "אולי נמשיך", "בוא נמשיך", "מה עכשיו",
        "זהו", "די", "אין עוד",
        
        # English
        "i told you", "already said", "already answered",
        "nothing happened", "nothing else",
        "let's continue", "let's move on", "what now"
    ]
    
    msg_lower = user_message.lower()
    return any(signal in msg_lower for signal in continue_signals)


def _check_event_criteria_bsd(state: Dict[str, Any], language: str = "he") -> Tuple[bool, List[str]]:
    """
    BSD methodology: אירוע מפורט = מתי + איפה + מי + מה קרה.
    Returns (has_sufficient, list of missing: "מתי"|"איפה"|"מי"|"מה").
    """
    collected = _safe_collected_dict(state.get("collected_data"))
    event_desc = collected.get("event_description") or ""
    messages = state.get("messages", [])
    recent_user = [
        msg.get("content", "")
        for msg in messages[-10:]
        if isinstance(msg, dict) and (msg.get("sender") == "user" or msg.get("role") == "user") and msg.get("content")
    ]
    all_text = " ".join(recent_user).lower() if recent_user else ""

    # Fast path: LLM extracted structured event
    if event_desc and len(event_desc.strip()) >= 40:
        return True, []

    if len(recent_user) < 2:
        return False, ["מתי", "איפה", "מי", "מה"]

    missing: List[str] = []

    # מתי - מסגרת זמן ספציפית (לא "כשאני לחוץ" - זה תנאי, לא זמן)
    mati_he = ["אתמול", "שבועיים", "לפני שבוע", "לפני חודש", "ביום שישי", "בשבוע שעבר", "בחודש שעבר", "לא מזמן", "לאחרונה"]
    mati_en = ["yesterday", "last week", "last month", "a few weeks", "recently"]
    mati_ok = any(p in all_text for p in mati_he) or any(p in all_text for p in mati_en)
    if not mati_ok:
        missing.append("מתי")

    # איפה - מיקום/זירה
    eyfa_he = ["בבית", "בחדר", "בסלון", "בעבודה", "במשרד", "בפגישה", "באוטו", "במטבח", "בכניסה"]
    eyfa_en = ["at home", "at work", "in the", "in a meeting"]
    eyfa_ok = any(p in all_text for p in eyfa_he) or any(p in all_text for p in eyfa_en)
    if not eyfa_ok:
        missing.append("איפה")

    # מי - אנשים מעורבים (לא "אני" לבד)
    mi_he = ["אשתי", "בעלי", "בן ", "בת ", "חבר", "עמית", "מנהל", "בוס", "ילדים", "משפחה", "עם ", "איתה", "איתו"]
    mi_en = ["wife", "husband", "son", "daughter", "friend", "boss", "manager", "with "]
    mi_ok = any(p in all_text for p in mi_he) or any(p in all_text for p in mi_en)
    if not mi_ok:
        missing.append("מי")

    # מה - מה קרה (אינטראקציה, דיאלוג, תגובה)
    ma_he = ["קרה", "אמר", "אמרה", "שאל", "הגיב", "נאמר", "נפגע", "דיברנו", "שיחה", "מריבה", "ראיתי", "שמעתי", "מתייחס"]
    ma_en = ["said", "asked", "happened", "told", "talked", "argued", "saw", "heard"]
    ma_ok = any(p in all_text for p in ma_he) or any(p in all_text for p in ma_en)
    if not ma_ok:
        missing.append("מה")

    # BSD: אם יש 3+ מ-4 = מספיק (גמישות סבירה)
    has_enough = (mati_ok and mi_ok and ma_ok) or (eyfa_ok and mi_ok and ma_ok)
    if has_enough:
        return True, []
    return False, missing if missing else ["מתי", "איפה", "מי", "מה"]


def has_sufficient_event_details(state: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Check if we have enough event details per BSD: מתי, איפה, מי, מה קרה.
    Returns (has_sufficient, reason_if_not) - reason is comma-separated missing criteria.
    """
    has_enough, missing = _check_event_criteria_bsd(state)
    if has_enough:
        return True, ""
    if not missing:
        return False, "need_more_responses"
    return False, ",".join(missing)


def get_explanatory_response_for_missing_details(reason: str, language: str) -> str:
    """
    BSD-aligned: ask TARGETED questions based on what's missing (מתי, איפה, מי, מה).
    """
    missing = [m.strip() for m in reason.split(",") if m.strip()] if reason else []
    if not missing:
        missing = ["מתי", "איפה", "מי", "מה"]

    if language == "he":
        # שאלות ממוקדות לפי מה שחסר (BSD: מתי, איפה, מי, מה)
        q = []
        if "מתי" in missing:
            q.append("מתי זה היה לאחרונה? לפני שבוע? אתמול?")
        if "איפה" in missing:
            q.append("איפה הייתם? בבית? בעבודה? בשיחה?")
        if "מי" in missing:
            q.append("עם מי היה? מי עוד היה שם?")
        if "מה" in missing:
            q.append("מה בדיוק קרה? מה נאמר? איך הגיבו?")
        if not q:
            q = ["מה בדיוק קרה שם?"]
        prefix = "אני מבין שאתה רוצה להמשיך. כדי שנוכל לזהות את הדפוס, אני צריך רגע אחד ספציפי. "
        return prefix + " ".join(q)
    else:
        q = []
        if "מתי" in missing:
            q.append("When did it happen? Last week? Recently?")
        if "איפה" in missing:
            q.append("Where were you? At home? At work?")
        if "מי" in missing:
            q.append("Who was there? Who else was involved?")
        if "מה" in missing:
            q.append("What exactly happened? What was said? How did they react?")
        if not q:
            q = ["What exactly happened there?"]
        prefix = "I understand you want to continue. To identify your pattern, I need one specific moment. "
        return prefix + " ".join(q)


def _safe_stage_index(step: Any, stage_order: List[str]) -> int:
    """Return stage index or -1 if invalid. Never raises."""
    if step is None or not isinstance(step, str):
        return -1
    s = step.strip()
    return stage_order.index(s) if s in stage_order else -1


def validate_stage_transition(
    old_step: str,
    new_step: str,
    state: Dict[str, Any],
    language: str,
    coach_message: str = "",
    user_message: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Safety net: validate if stage transition is premature.
    
    Args:
        old_step: Current step before transition
        new_step: Proposed new step
        state: Current conversation state
        language: "he" or "en"
        coach_message: The LLM's proposed message (to check if already in new stage)
    
    Returns:
        (is_valid, correction_message)
        - If is_valid=True, allow the transition
        - If is_valid=False, return correction message to override LLM response
    """
    # Compute stage indexes once - ALWAYS set (guards against UnboundLocalError)
    stage_order = ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12", "S13"]
    old_idx = _safe_stage_index(old_step, stage_order)
    new_idx = _safe_stage_index(new_step, stage_order)

    # GENERIC SOLUTION: Check if user wants to move on
    recent_user_messages = [
        msg.get("content", "").lower() for msg in state.get("messages", [])[-3:]
        if msg.get("sender") == "user"
    ]
    
    if language == "he":
        move_on_keywords = [
            "מסכם", "זה הכל", "זהו", "נתקדם", "הלאה", "די", "די לי",
            "כל הרגשות", "כבר כתבתי", "בוא נתקדם", "מה הלאה",
            "אמרתי כבר", "כבר אמרתי", "עניתי", "זה מספיק", "לא"
        ]
    else:
        move_on_keywords = [
            "that's all", "let's move", "move on", "enough", "that's it",
            "i already said", "already told", "move forward", "what's next"
        ]
    
    user_wants_to_move_on = any(
        keyword in msg for msg in recent_user_messages
        for keyword in move_on_keywords
    )
    
    # If user explicitly wants to move on, ALWAYS allow transition
    if user_wants_to_move_on:
        logger.info(f"[Safety Net] User wants to move on - allowing {old_step}→{new_step}")
        return True, None
    
    # Otherwise, check minimum turns for critical transitions
    
    # 🚨 CRITICAL: S1→S2 - Must have clear topic!
    if old_step == "S1" and new_step == "S2":
        has_topic, reason = has_clear_topic_for_s2(state, user_message=user_message)
        
        if not has_topic:
            logger.warning(f"[Safety Net] Blocking S1→S2: topic not clear ({reason})")
            if language == "he":
                return False, "אני מבין שאתה רוצה להמשיך. אבל **לפני שניקח אירוע ספציפי, אני צריך להבין בדיוק על מה אתה רוצה להתאמן**. ספר לי - מה מעסיק אותך?"
            else:
                return False, "I understand you want to continue. But **before we take a specific event, I need to understand exactly what you want to work on**. Tell me - what's on your mind?"
    
    # 🚨 CRITICAL: Block S1→S3 (can't skip S2 event!)
    if old_step == "S1" and new_step == "S3":
        # ✅ EXCEPTION: If user already gave event details, allow S3 (state may be stale)
        has_event, _ = has_sufficient_event_details(state)
        # ✅ EXCEPTION: User gave event in CURRENT message (not in state yet) - e.g. "אתמול עם בעלי..."
        user_gave_event_in_msg = False
        if user_message and len(user_message.strip()) >= 30:
            um_lower = user_message.lower()
            event_indicators = ["אתמול", "לפני", "שבוע", "חודש", "בעלי", "אשתי", "בן ", "בת ", "חבר", "קרה", "אמר", "דיברנו", "שיחה", "yesterday", "husband", "wife", "said", "happened"]
            user_gave_event_in_msg = any(p in um_lower for p in event_indicators)
        if has_event or user_gave_event_in_msg:
            logger.info(f"[Safety Net] User already gave event (state or current msg) → allowing S1→S3")
            return True, None
        logger.error(f"[Safety Net] 🚫 BLOCKED S1→S3: Cannot skip S2 (event)!")
        topic = _safe_get_topic_from_collected(state.get("collected_data"))
        # Sanitize: LLM might copy placeholder "[נושא]" from prompt
        if topic and ("[" in topic or "]" in topic or topic.strip() in ("[נושא]", "[topic]")):
            topic = ""
        if not topic:
            # Fallback: use first substantial user message as topic hint (e.g. "לומר לא", "נאמנות לעצמי")
            # Skip greetings/meta: "מה שמך?", "שלום" - prefer topic messages (len >= 10)
            skip_for_topic = ("מה שמך", "שלום", "היי", "what's your name", "hello", "hi")
            for msg in (state.get("messages") or []):
                if msg.get("sender") == "user":
                    content = (msg.get("content") or "").strip()
                    if len(content) >= 10 and len(content) <= 80:
                        if not any(skip in content.lower() for skip in skip_for_topic):
                            topic = content
                            break
        if language == "he":
            if topic:
                msg = f"בוא ניקח **אירוע ספציפי אחד** שקרה לאחרונה. ספר לי על פעם אחת ש{topic} - מתי זה היה? עם מי?"
            else:
                msg = "בוא ניקח **אירוע ספציפי אחד** שקרה לאחרונה. ספר לי על פעם אחת - מתי זה היה? עם מי?"
            return False, msg
        else:
            if topic:
                msg = f"Let's take **one specific event** that happened recently. Tell me about one time when {topic} - when was it? Who was there?"
            else:
                msg = "Let's take **one specific event** that happened recently. Tell me about one time - when was it? Who was there?"
            return False, msg
    
    # 🚨 CRITICAL: Block S1→S4, S1→S5, etc. (can't skip multiple stages!)
    if old_step == "S1" and new_idx > 2:
        # ✅ EXCEPTION: If user already gave event details (e.g. re_ask_check moved us), allow
        has_event, _ = has_sufficient_event_details(state)
        if has_event:
            logger.info(f"[Safety Net] User already gave event → allowing S1→{new_step}")
            return True, None
        logger.error(f"[Safety Net] 🚫 BLOCKED S1→{new_step}: Cannot skip S2!")
        if language == "he":
            return False, "רגע, בוא קודם ניקח אירוע ספציפי אחד. ספר לי על פעם אחת לאחרונה - מתי זה היה?"
        else:
            return False, "Wait, let's first take one specific event. Tell me about one time recently - when was it?"
    
    # 🚨 CRITICAL: Block S2→S4 (can't skip S3 emotions!)
    if old_step == "S2" and new_step == "S4":
        logger.error(f"[Safety Net] 🚫 BLOCKED S2→S4: Cannot skip S3 (emotions)!")
        if language == "he":
            return False, "רגע, לפני שנדבר על מחשבות - ספר לי קודם **מה הרגשת** באותו רגע?"
        else:
            return False, "Wait, before we talk about thoughts - tell me first **what did you feel** in that moment?"
    
    # 🚨 CRITICAL: Block backwards transitions (can't go backwards!)
    # Don't allow going backwards (except to S0/S1 which are resets)
    if old_idx >= 2 and new_idx >= 2 and new_idx < old_idx:
        logger.error(f"[Safety Net] 🚫 BLOCKED backwards transition {old_step}→{new_step}")
        if language == "he":
            return False, "בוא נמשיך הלאה במקום לחזור אחורה."
        else:
            return False, "Let's move forward instead of going backwards."
    
    # S2→S3: Need detailed event (at least 3 turns in S2)
    if old_step == "S2" and new_step == "S3":
        s2_turns = count_turns_in_step(state, "S2")
        
        # 🚨 CRITICAL: Check if stuck in loop
        if detect_stuck_loop(state):
            logger.error(f"[Safety Net] 🔄 LOOP DETECTED! Forcing progression to S3")
            return True, None  # Force progression!
        
        # 🚨 CRITICAL: Check if user already gave emotions (wrong stage!)
        if user_already_gave_emotions(state):
            logger.info(f"[Safety Net] ✅ User already gave emotions, allowing S2→S3 transition")
            return True, None  # Allow transition
        
        # 🚨 NEW LOGIC: Check if user is frustrated
        user_msg = state.get("messages", [])[-1].get("content", "") if state.get("messages") else ""
        if user_wants_to_continue(user_msg):
            logger.warning(f"[Safety Net] 🤔 User frustrated - checking if we have sufficient info...")
            
            # Check if we actually have enough event details
            has_info, reason = has_sufficient_event_details(state)
            
            if has_info:
                # Good to go - user is frustrated but we have enough info
                logger.info(f"[Safety Net] ✅ User frustrated BUT has sufficient details → allowing S2→S3")
                return True, None
            else:
                # Need more info - EXPLAIN why instead of just asking again
                logger.warning(f"[Safety Net] ⚠️ User frustrated BUT missing details ({reason}) → explaining")
                explanation = get_explanatory_response_for_missing_details(reason, language)
                return False, explanation
        
        # 🎯 Check if LLM already asked an S3 question (emotions)
        # If yes, allow the transition even if s2_turns < 3
        # This prevents overriding good LLM responses
        if language == "he":
            s3_indicators = ["מה הרגשת", "איזה רגש", "מה עבר בך", "מה נגע בך", "התעמק ברגשות"]
        else:
            s3_indicators = ["what did you feel", "what emotion", "how did you feel", "feelings", "emotions"]
        
        llm_already_in_s3 = any(indicator in coach_message.lower() for indicator in s3_indicators)
        
        if llm_already_in_s3:
            logger.info(f"[Safety Net] LLM already asked S3 question, allowing transition despite {s2_turns} turns")
            return True, None  # Allow transition
        
        # If LLM hasn't moved to S3 yet: use BSD-aligned targeted questions (מתי, איפה, מי, מה)
        if s2_turns < 3:
            has_info, reason = has_sufficient_event_details(state)
            if has_info:
                return True, None  # We have enough per BSD criteria
            logger.warning(f"[Safety Net] Blocked S2→S3: missing ({reason})")
            question = get_explanatory_response_for_missing_details(reason, language)
            return False, question
    
    # S3→S4: Need emotions (at least 3 turns in S3)
    if old_step == "S3" and new_step == "S4":
        s3_turns = count_turns_in_step(state, "S3")
        
        # 🚨 CRITICAL: Check if stuck in loop
        if detect_stuck_loop(state):
            logger.error(f"[Safety Net] 🔄 LOOP DETECTED! Forcing progression to S4")
            return True, None  # Force progression!
        
        # 🚨 NEW LOGIC: Check if user is frustrated
        user_msg = state.get("messages", [])[-1].get("content", "") if state.get("messages") else ""
        if user_wants_to_continue(user_msg):
            logger.warning(f"[Safety Net] 🤔 User frustrated in S3 - checking if we have sufficient emotions...")
            
            # For S3, if user already gave emotions, that's usually enough
            # Check if we have at least some emotion words
            if user_already_gave_emotions(state):
                logger.info(f"[Safety Net] ✅ User frustrated BUT has emotions → allowing S3→S4")
                return True, None
            else:
                # Missing emotions - explain why we need them
                logger.warning(f"[Safety Net] ⚠️ User frustrated BUT no emotions yet → explaining")
                if language == "he":
                    explanation = (
                        "אני מבין שאתה רוצה להמשיך. "
                        "הסיבה שאני צריך לשמוע על הרגשות שלך היא שהן חלק מרכזי בדפוס - "
                        "הדפוס הוא השילוב של המצב, הרגש והמחשבה שחוזרים. "
                        "מה הרגשת באותו רגע?"
                    )
                else:
                    explanation = (
                        "I understand you want to continue. "
                        "The reason I need to hear about your emotions is that they're a central part of the pattern - "
                        "the pattern is the combination of situation, emotion, and thought that repeats. "
                        "What did you feel in that moment?"
                    )
                return False, explanation
        
        # 🎯 Check if LLM already asked an S4 question (thoughts)
        # If yes, allow the transition even if s3_turns < 3
        if language == "he":
            s4_indicators = ["מה עבר לך בראש", "מה חשבת", "מה אמרת לעצמך", "איזה משפט", "מחשב"]
        else:
            s4_indicators = ["what went through your mind", "what did you think", "what did you tell yourself", "thought"]
        
        llm_already_in_s4 = any(indicator in coach_message.lower() for indicator in s4_indicators)
        
        if llm_already_in_s4:
            logger.info(f"[Safety Net] LLM already asked S4 question, allowing transition despite {s3_turns} turns")
            return True, None  # Allow transition
        
        # If user already gave emotions (2+), allow S3→S4 - no need to drill each one
        if user_already_gave_emotions(state):
            logger.info(f"[Safety Net] User gave emotions → allowing S3→S4 (no per-emotion drilling)")
            return True, None
        
        # If LLM hasn't moved to S4 yet, check turns count
        if s3_turns < 3:
            logger.warning(f"[Safety Net] Blocked S3→S4: only {s3_turns} turns in S3")
            if language == "he":
                return False, "מה עוד הרגשת באותו רגע?"
            else:
                return False, "What else did you feel in that moment?"
    
    # S8→S9: Need pattern confirmation
    if old_step == "S8" and new_step == "S9":
        # Check if user explicitly said they don't understand the pattern
        if language == "he":
            confusion_keywords = ["לא יודע מה הדפוס", "לא מבין מה הדפוס", "מה הדפוס", "איזה דפוס"]
        else:
            confusion_keywords = ["don't know the pattern", "what pattern", "which pattern", "what is the pattern"]
        
        user_confused = any(
            keyword in msg for msg in recent_user_messages
            for keyword in confusion_keywords
        )
        
        if user_confused:
            logger.warning(f"[Safety Net] Blocked S8→S9: user doesn't understand the pattern yet")
            if language == "he":
                # Need to explicitly summarize the pattern
                return False, "אני מבין. בוא נסכם: הדפוס הוא שאתה מגיב בדרך מסוימת במצבים שונים. מה התגובה שלך שחוזרת? מה משותף בין המצבים שתיארת?"
            else:
                return False, "I understand. Let's summarize: the pattern is that you respond in a certain way in different situations. What's your response that repeats? What's common between the situations you described?"
        
        # 🚨 NEW: Check if user already gave examples and said so
        user_msg = state.get("messages", [])[-1].get("content", "") if state.get("messages") else ""
        example_count = count_pattern_examples_in_s7(state)
        
        if example_count >= 2 and user_said_already_gave_examples(user_msg):
            logger.info(f"[Safety Net] User gave {example_count} examples + said 'already told' → allowing S8→S9")
            return True, None
        
        # 🚨 NEW: Check if stuck in loop asking "where else?"
        if detect_stuck_loop(state) and example_count >= 2:
            logger.error(f"[Safety Net] LOOP in S8 with {example_count} examples → forcing S9")
            return True, None
        
        # Check if we have sufficient examples (content-based, not just turns)
        s8_turns = count_turns_in_step(state, "S8")
        
        if example_count >= 2 and s8_turns >= 3:
            # Has enough examples and turns → allow transition
            logger.info(f"[Safety Net] S8 has {example_count} examples + {s8_turns} turns → allowing S8→S9")
            return True, None
        
        if s8_turns < 3:
            logger.warning(f"[Safety Net] Blocked S8→S9: only {s8_turns} turns and {example_count} examples")
            if language == "he":
                # GENERIC: Varied questions to explore pattern depth
                pattern_questions = [
                    "איפה עוד אתה מזהה את התגובה הזו שלך?",
                    "האם זה קורה רק במצבים מסוימים, או גם במקומות אחרים?",
                    "מה משותף לכל המצבים שתיארת? מה **אתה** עושה שחוזר?"
                ]
                question = pattern_questions[min(s8_turns, len(pattern_questions) - 1)]
                return False, question
            else:
                pattern_questions = [
                    "Where else do you recognize this response of yours?",
                    "Does this happen only in certain situations, or in other places too?",
                    "What's common to all the situations you described? What do **you** do that repeats?"
                ]
                question = pattern_questions[min(s8_turns, len(pattern_questions) - 1)]
                return False, question
    
    # All other transitions: trust the LLM
    return True, None


# ══════════════════════════════════════════════════════════════════════════════
# CONTEXT BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_conversation_context(
    state: Dict[str, Any],
    user_message: str,
    language: str
) -> str:
    """
    Build rich context for LLM.
    
    Includes:
    - Current state (step, collected data)
    - Recent conversation history
    - User's new message
    
    Args:
        state: Current conversation state
        user_message: User's new message
        language: "he" or "en"
    
    Returns:
        Context string for LLM
    """
    # Context window tuning (preserve methodology, reduce repetitive token load)
    # Default keeps enough turns for BSD stage continuity while avoiding long-tail drift.
    history_last_n = int(os.getenv("BSD_V2_HISTORY_LAST_N", "8"))
    max_msg_chars = int(os.getenv("BSD_V2_HISTORY_MSG_MAX_CHARS", "420"))

    # Some stages benefit from slightly wider local context.
    if state.get("current_step") in {"S2", "S3", "S8"}:
        history_last_n = max(history_last_n, 10)

    # Get recent history
    history = get_conversation_history(state, last_n=history_last_n)
    logger.info(
        f"[BSD V2 CONTEXT] History window={history_last_n}, max_msg_chars={max_msg_chars}, loaded={len(history)}"
    )
    
    # Build context
    context_parts = []
    
    # Current state
    context_parts.append("# מצב נוכחי" if language == "he" else "# Current State")
    context_parts.append(f"שלב: {state['current_step']}" if language == "he" else f"Stage: {state['current_step']}")
    context_parts.append(f"Saturation Score: {state['saturation_score']:.1f}")
    
    # Collected data (non-null only)
    collected = {k: v for k, v in state['collected_data'].items() if v is not None and v != [] and v != {}}
    if collected:
        context_parts.append("\nנתונים שנאספו:" if language == "he" else "\nCollected Data:")
        context_parts.append(json.dumps(collected, ensure_ascii=False, indent=2))
        if state.get("current_step") in ("S5", "S6", "S7"):
            context_parts.append("\n🚨 השתמש בנתונים האלה לבניית הסיכום! אל תסכם בלי לדעת מה נאסף." if language == "he" else "\n🚨 Use this data to build the summary! Don't summarize without knowing what was collected.")
    
    # Extract event details from history for S2 (to prevent repeated questions)
    if state['current_step'] == 'S2' and history:
        event_summary = []
        for msg in history:
            if msg['sender'] == 'user':
                content = msg['content'].lower()
                # Check for location mentions
                if 'בחדר' in content or 'בבית' in content or 'במקום' in content:
                    event_summary.append(f"✓ מקום כבר נאמר: {msg['content'][:80]}...")
                # Check for time mentions
                if 'אתמול' in content or 'שישי' in content or 'שבוע' in content or 'חודש' in content:
                    event_summary.append(f"✓ זמן כבר נאמר: {msg['content'][:80]}...")
                # Check for people mentions
                if 'אשתי' in content or 'בת זוג' in content or 'ילדים' in content:
                    event_summary.append(f"✓ מי כבר נאמר: {msg['content'][:80]}...")
        
        if event_summary:
            context_parts.append("\n🚨 חשוב - פרטים שכבר נאמרו על האירוע:" if language == "he" else "\n🚨 Important - Event details already mentioned:")
            context_parts.extend(event_summary)
            if language == "he":
                context_parts.append("⚠️ אל תשאל שוב על פרטים שכבר נאמרו!")
            else:
                context_parts.append("⚠️ Don't ask again about details already mentioned!")
    
    # Conversation history with EMPHASIS
    if history:
        context_parts.append("\n# היסטוריה אחרונה - קרא בעיון!" if language == "he" else "\n# Recent History - Read Carefully!")
        if language == "he":
            context_parts.append("🚨 חשוב: אל תשאל שאלות שהמשתמש כבר ענה עליהן בהיסטוריה!")
        else:
            context_parts.append("🚨 Important: Don't ask questions the user already answered in the history!")
        
        for msg in history:
            sender_value = msg.get("sender", "unknown")
            content_value = msg.get("content", "")
            if not content_value:  # Skip empty messages
                continue
            # Keep only the informative head of long turns to reduce repeated token cost.
            if len(content_value) > max_msg_chars:
                content_value = content_value[:max_msg_chars] + " ...[truncated]"
            sender = "משתמש" if sender_value == "user" else "מאמן"
            if language == "en":
                sender = "User" if sender_value == "user" else "Coach"
            context_parts.append(f"{sender}: {content_value}")
    
    # New message
    context_parts.append("\n# הודעה חדשה" if language == "he" else "\n# New Message")
    context_parts.append(f"משתמש: {user_message}" if language == "he" else f"User: {user_message}")
    # Strong JSON instruction (last thing model sees) - helps when API doesn't enforce format
    context_parts.append("\n\n🚨 **חובה:** החזר רק אובייקט JSON תקין עם coach_message ו-internal_state. בלי טקסט חופשי." if language == "he" else "\n\n🚨 **Required:** Return ONLY a valid JSON object with coach_message and internal_state. No free text.")
    
    context = "\n".join(context_parts)
    logger.info(
        f"[PERF] Context size chars={len(context)}, history_msgs={len(history)}, step={state.get('current_step')}"
    )
    return context


# ══════════════════════════════════════════════════════════════════════════════
# MAIN HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle_conversation(
    user_message: str,
    state: Dict[str, Any],
    language: str = "he",
    user_gender: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Handle single conversation turn in V2.
    
    Flow:
    1. Build context from state + history + new message
    2. Call LLM with system prompt
    3. Parse JSON response
    4. Extract coach message and internal state
    5. Update state
    6. Return (coach_message, updated_state)
    
    Args:
        user_message: User's message
        state: Current conversation state
        language: "he" or "en"
    
    Returns:
        (coach_message, updated_state)
    """
    # Per-turn debug: repetition & stage transition tracking
    overrides_applied: List[str] = []
    if SAFETY_NET_DISABLED:
        logger.warning("[Safety Net] DISABLED (BSD_V2_SAFETY_NET_DISABLED=1)")
    _bsd_log("TURN_START", step=state['current_step'], saturation=state['saturation_score'],
             msg_count=len(state.get('messages', [])), user_preview=user_message[:80])
    logger.info(f"[BSD V2] Handling message: '{user_message[:50]}...'")
    logger.info(f"[BSD V2] Current step: {state['current_step']}, saturation: {state['saturation_score']:.2f}")
    logger.info(f"[BSD V2] Message count in state: {len(state.get('messages', []))}")
    
    # 🚨 CRITICAL: Check if user is asking about unrelated event
    if not SAFETY_NET_DISABLED and state["current_step"] == "S2" and user_questions_unrelated_event(user_message):
        logger.info(f"[Safety Net] User asking about unrelated event - explaining directly")
        if language == "he":
            explanation = """שאלה מעולה! הסיטואציה **לא חייבת** להיות קשורה לנושא האימון.

למה? כי **הדפוס שלך הולך איתך לכל מקום** - לבית, לעבודה, לחברים, לכל תחום בחיים.

לפעמים דווקא באירוע מתחום **אחר לגמרי** (למשל: שיחה עם חבר, מצב בעבודה, אינטראקציה עם בן משפחה) הדפוס מתגלה בצורה הכי **נקייה וברורה** - בלי הרבה "רעש" סביב.

אז תרגיש חופשי לשתף אירוע מכל תחום שבו היית באינטראקציה עם אנשים והרגשת סערה רגשית. מה עולה לך?"""
        else:
            explanation = """Great question! The situation **doesn't have to** be related to the coaching topic.

Why? Because **your pattern goes with you everywhere** - home, work, friends, every area of life.

Sometimes a situation from a **completely different area** (e.g., conversation with a friend, situation at work, interaction with family) reveals the pattern most **clearly** - without a lot of "noise" around it.

So feel free to share an event from any area where you interacted with people and felt emotional turmoil. What comes to mind?"""
        
        # Add this as a coach response directly, no need for LLM
        internal_state = {
            "current_step": state["current_step"],  # Stay in same stage
            "saturation_score": state.get("saturation_score", 0.3),
            "reflection": "Explained why event doesn't need to be related to topic"
        }
        state = add_message(state, "user", user_message)
        state = add_message(state, "coach", explanation, internal_state)
        return explanation, state
    
    # 🚨 CRITICAL: Clarification requests ("אתה יכול להסביר?", "מה כוונתך?") ≠ frustration!
    # Per s1_topic.md: user wants EXPLANATION, not to move on. Give explanation, stay in S1.
    clarification_only_phrases_he = ["מה כוונה", "מה הכוונה", "לא הבנתי", "מה כוונתך", "אתה יכול להסביר", "מה חסר", "למה אתה חוקר"]
    clarification_only_phrases_en = ["what do you mean", "i don't understand", "can you explain", "what's missing", "why are you asking"]
    user_msg_lower = (user_message or "").lower()
    is_clarification_only = (
        (language == "he" and any(p in user_msg_lower for p in clarification_only_phrases_he))
        or (language == "en" and any(p in user_msg_lower for p in clarification_only_phrases_en))
    )
    # Real frustration = "אמרתי כבר", "די כבר" - wants to move on
    real_frustration_phrases_he = [
        "אמרתי כבר", "אמרתי לך", "כבר אמרתי", "כבר סיפרתי",
        "ספרתי לך", "ספרתי לך על", "עשינו זאת כבר", "בוא נתקדם",
        "זה חוזר שוב", "זה חוזר", "כבר ספרתי על",
        "חזרת על עצמך", "אתה חוזר", "עניתי כבר", "עניתי לך",
        "עניתי הכי טוב", "עניתי הכי טוב שהצלחתי", "זה הכי טוב שיכולתי",
        "די כבר", "די די", "מספיק כבר", "די לי כבר",
    ]
    real_frustration_phrases_en = [
        "i already said", "i told you", "already told you", "i told you about",
        "you're repeating", "i already answered", "stop repeating",
        "this is repeating", "it keeps repeating",
        "i answered the best i could", "that's the best i could do",
    ]
    has_real_frustration = (
        (language == "he" and any(p in user_msg_lower for p in real_frustration_phrases_he))
        or (language == "en" and any(p in user_msg_lower for p in real_frustration_phrases_en))
    )

    if not SAFETY_NET_DISABLED and is_clarification_only and not has_real_frustration and state.get("current_step") == "S1":
        # User asked for explanation - give it, stay in S1. Do NOT jump to S2!
        logger.info(f"[Safety Net] User asked for clarification ('{user_message[:40]}...') - explaining, staying in S1")
        if language == "he":
            explanation = "אני שואל עוד כי הנושא צריך להיות מוגדר היטב לפני שנמשיך. כדי לאמן אותך, אני צריך להבין במדויק על מה אתה רוצה להתאמן."
            has_topic, _ = has_clear_topic_for_s2(state)
            if has_topic:
                topic_hint = _safe_get_topic_from_collected(state.get("collected_data"))
                for msg in reversed(state.get("messages", [])):
                    if msg.get("sender") == "user":
                        c = (msg.get("content") or "").strip()
                        if c and len(c) > 3 and not any(p in c.lower() for p in clarification_only_phrases_he):
                            topic_hint = topic_hint or (c[:40] + "..." if len(c) > 40 else c)
                            break
                if topic_hint:
                    explanation += f" מה בדיוק ב\"{topic_hint}\" מעסיק אותך?"
        else:
            explanation = "I'm asking more because the topic needs to be well defined before we continue. To coach you, I need to understand exactly what you want to work on."
        state = add_message(state, "user", user_message)
        state = add_message(state, "coach", explanation, {"current_step": "S1", "saturation_score": state.get("saturation_score", 0.3), "reflection": "Explained why we need more clarity"})
        return explanation, state

    # Check if user is frustrated (wants to move on) - Use EXPLICIT phrases only
    user_frustrated = has_real_frustration and not SAFETY_NET_DISABLED

    if user_frustrated:
        _bsd_log("USER_FRUSTRATED", step=state['current_step'], user_msg=user_message[:60])
        logger.warning(f"[Safety Net] User is frustrated ('{user_message}') - checking if can progress")
        current_step = state['current_step']
        
        # Add user message first
        state = add_message(state, "user", user_message)
        
        # 🎯 SPECIAL HANDLING FOR S1 - check if topic/event before progressing
        if current_step == "S1":
            has_event, _ = has_sufficient_event_details(state)
            has_topic, reason = has_clear_topic_for_s2(state)
            
            if has_event:
                # ✅ User already gave event - move to S3 (emotions)!
                logger.info(f"[Safety Net] User frustrated in S1, but already gave event → moving to S3")
                if language == "he":
                    apology_message = "מצטער על החזרה! שמעתי על האירוע. עכשיו – מה הרגשת באותו רגע?"
                else:
                    apology_message = "Sorry for repeating! I heard about the event. Now – what did you feel in that moment?"
                next_step = "S3"
            elif has_topic:
                # ✅ Topic is clear - can progress to S2
                logger.info(f"[Safety Net] User frustrated/confused in S1, but topic is clear → moving to S2")
                confusion_phrases = ["מה הכונה", "מה הכוונה", "לא הבנתי", "מה כוונתך", "what do you mean", "i don't understand"]
                is_confusion = any(p in user_message.lower() for p in confusion_phrases)
                if language == "he":
                    prefix = "סליחה על השאלה המסובכת. " if is_confusion else "אני מבין. "
                else:
                    prefix = "Sorry for the confusing question. " if is_confusion else "I understand. "
                apology_message = f"{prefix}{get_next_step_question(current_step, language)}"
                next_step = "S2"
            else:
                # ⚠️ Topic not clear - EXPLAIN why we need more info
                logger.warning(f"[Safety Net] User frustrated in S1, but topic not clear ({reason}) → explaining")
                apology_message = get_s1_explanation_for_missing_info(reason, language)
                next_step = "S1"  # Stay in S1 but with explanation
        else:
            # For other stages, use standard progression
            if language == "he":
                apology_message = f"מצטער על החזרה! {get_next_step_question(current_step, language)}"
            else:
                apology_message = f"Sorry for repeating! {get_next_step_question(current_step, language)}"
            
            # Determine next step
            step_progression = {
                "S0": "S1", "S1": "S2", "S2": "S3", "S3": "S4",
                "S4": "S5", "S5": "S6", "S6": "S7", "S7": "S8",
                "S8": "S9", "S9": "S10", "S10": "S11", "S11": "S12", "S12": "S13"
            }
            next_step = step_progression.get(current_step, current_step)
        
        # Add coach response
        internal_state = {
            "current_step": next_step,
            "saturation_score": 0.3,
            "reflection": f"User frustrated - moving from {current_step} to {next_step}"
        }
        state = add_message(state, "coach", apology_message, internal_state)
        
        return apology_message, state
    
    try:
        start_time = time.time()
        
        # 1. Build context
        t1 = time.time()
        context = build_conversation_context(state, user_message, language)
        t2 = time.time()
        logger.info(f"[PERF] Build context: {(t2-t1)*1000:.0f}ms ({len(context)} chars)")
        
        # 2. Prepare messages using modular stage-aware prompt assembly.
        current_step = state.get("current_step", "S1")
        system_prompt = _get_system_prompt(state=state, user_message=user_message, language=language, user_gender=user_gender)
        logger.info(
            "[PERF] System prompt chars from prompt_manager: %s",
            len(system_prompt),
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context)
        ]
        
        # 3. Call LLM
        t3 = time.time()
        coach_message = ""
        internal_state: Dict[str, Any] = {}

        if USE_GEMINI:
            from langchain_google_genai import ChatGoogleGenerativeAI, HarmCategory, HarmBlockThreshold
            logger.info("[BSD V2] Using Google Gemini Engine (Optimized for Coaching)")

            # Critical for coaching: Disable safety blocks to allow users to express negative emotions/hardship freely
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            gemini_llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                temperature=0.2,
                max_retries=2,
                safety_settings=safety_settings
            )

            structured_llm = gemini_llm.with_structured_output(CoachResponseSchema)
            response = await structured_llm.ainvoke(messages)

            coach_message = response.coach_message
            internal_state = response.internal_state.model_dump()
            llm = gemini_llm
            _bsd_log("LLM_DECISION", step=internal_state.get("current_step"),
                     saturation=internal_state.get("saturation_score"),
                     collected_data_keys=list(_safe_collected_dict(internal_state.get("collected_data")).keys()),
                     coach_preview=(coach_message or "")[:60])
        else:
            # Azure OpenAI path (existing logic)
            use_structured = os.getenv("BSD_V2_STRUCTURED_OUTPUT", "1").strip() in ("1", "true", "yes")

            if use_structured:
                llm = get_azure_chat_llm(purpose="talker")
                try:
                    strict = os.getenv("BSD_V2_STRUCTURED_STRICT", "1").strip() in ("1", "true", "yes")
                    structured_llm = llm.with_structured_output(
                        CoachResponseSchema, method="json_schema", strict=strict
                    )
                    response_obj = await structured_llm.ainvoke(messages)
                    coach_message = (response_obj.coach_message or "").strip()
                    internal_state = response_obj.internal_state.model_dump()
                    _bsd_log("LLM_DECISION", step=internal_state.get("current_step"),
                             saturation=internal_state.get("saturation_score"),
                             collected_data_keys=list(_safe_collected_dict(internal_state.get("collected_data")).keys()),
                             coach_preview=(coach_message or "")[:60])
                except Exception as e:
                    logger.warning(f"[BSD V2] Structured output failed ({e}), falling back to JSON mode")
                    use_structured = False

            if not use_structured:
                llm = get_azure_chat_llm(purpose="talker")
                if os.getenv("BSD_V2_JSON_MODE", "1").strip() in ("1", "true", "yes"):
                    llm = llm.bind(response_format={"type": "json_object"})
                cache_key_prefix = os.getenv("AZURE_OPENAI_PROMPT_CACHE_KEY_PREFIX", "bsd_v2_markdown_prompt")
                cache_key = f"{cache_key_prefix}:main_coach:{language}:{current_step}"
                response = await _ainvoke_with_prompt_cache(llm, messages, cache_key=cache_key)
                response_text = response.content.strip()
                token_usage = getattr(response, "response_metadata", {}).get("token_usage", {})
                prompt_token_details = token_usage.get("prompt_tokens_details", {})
                cached_tokens = prompt_token_details.get("cached_tokens")
                if cached_tokens is not None:
                    logger.info(f"[PERF] Prompt cache hit tokens: {cached_tokens}")
                try:
                    coach_message, internal_state = _parse_json_response(response_text, state, user_message, language)
                except json.JSONDecodeError as e:
                    logger.error(f"[BSD V2] Failed to parse JSON: {e}")
                    logger.error(f"[BSD V2] Response (first 200 chars): {repr((response_text or '')[:200])}")
                    coach_message = (response_text or "").strip()
                    # Infer step from coach message content - allows progression even without JSON
                    current_step = _infer_step_from_coach_message(coach_message, language) or state.get("current_step", "S1")
                    if current_step == "S0" and user_message and len(user_message.strip()) >= 2:
                        msg_count = len([m for m in state.get("messages", []) if isinstance(m, dict) and m.get("sender") == "user"])
                        if msg_count >= 1:
                            current_step = "S1"
                    collected = _safe_collected_dict(state.get("collected_data"))
                    if not collected.get("topic") and state.get("current_step") in ("S0", "S1"):
                        topic = _extract_topic_from_conversation(state, user_message, language)
                        if topic:
                            collected["topic"] = topic
                    internal_state = {
                        "current_step": current_step,
                        "saturation_score": state.get("saturation_score", 0.3),
                        "reflection": "Failed to parse (inferred step from content)",
                        "collected_data": collected,
                    }
                    if not coach_message:
                        coach_message = get_next_step_question(current_step, language)

        t4 = time.time()
        logger.info(f"[PERF] LLM call: {(t4-t3)*1000:.0f}ms")

        coach_message = _sanitize_coach_message(coach_message)
        
        # 5. Safety Net: Check for repeated questions
        t7 = time.time()
        history_for_check = get_conversation_history(state, last_n=10)
        repeated_check = check_repeated_question(coach_message, history_for_check, state['current_step'], language, user_message=user_message)
        t8 = time.time()
        logger.info(f"[PERF] Repeated check: {(t8-t7)*1000:.0f}ms")
        
        if not SAFETY_NET_DISABLED and repeated_check:
            overrides_applied.append("repetition")
            repl_msg = repeated_check[0] if isinstance(repeated_check, tuple) else repeated_check
            step_override = repeated_check[1] if isinstance(repeated_check, tuple) and len(repeated_check) > 1 else None
            _bsd_log("REPETITION_OVERRIDE", original=coach_message[:80], replacement=repl_msg[:80],
                     step=state['current_step'])
            logger.warning(f"[Safety Net] Overriding repeated question")
            coach_message = repl_msg
            internal_state["current_step"] = step_override if step_override else state["current_step"]
            internal_state["saturation_score"] = state.get("saturation_score", 0.3)
        
        # 5.5. Safety Net: Coach re-asking for event when user already gave it
        re_ask_check = detect_re_asking_for_event(coach_message, state, language, user_message=user_message) if not SAFETY_NET_DISABLED else None
        if re_ask_check:
            overrides_applied.append("re_ask_event")
            coach_message, next_step_for_reask = re_ask_check
            _bsd_log("RE_ASK_OVERRIDE", step=next_step_for_reask, reason="user_already_gave_event")
            internal_state["current_step"] = next_step_for_reask
            internal_state["saturation_score"] = 0.3
        
        # 6. Safety Net: Check for stage/question mismatch
        t9 = time.time()
        mismatch_stage = detect_stage_question_mismatch(coach_message, state["current_step"], language, state=state)
        t10 = time.time()
        logger.info(f"[PERF] Stage mismatch check: {(t10-t9)*1000:.0f}ms")
        
        if not SAFETY_NET_DISABLED and mismatch_stage:
            overrides_applied.append("stage_mismatch")
            _bsd_log("STAGE_MISMATCH", llm_step=internal_state.get("current_step"), corrected=mismatch_stage,
                     coach_preview=coach_message[:60])
            logger.warning(f"[Safety Net] Auto-correcting stage mismatch: {state['current_step']} → {mismatch_stage}")
            internal_state["current_step"] = mismatch_stage
        
        # 6.5. Safety Net: Validate situation quality (S2→S3 only)
        old_step = state["current_step"]
        new_step = internal_state.get("current_step", old_step)
        
        t11 = time.time()
        if not SAFETY_NET_DISABLED and old_step == "S2" and new_step == "S3":
            # Check if situation meets all 4 criteria
            logger.info(f"[Safety Net] Validating S2 situation quality before S2→S3...")
            situation_valid, guidance = await validate_situation_quality(state, llm, language)
            logger.info(f"[Safety Net] Validation result: valid={situation_valid}")
            if not situation_valid and guidance:
                overrides_applied.append("s2_quality_block")
                _bsd_log("S2_QUALITY_BLOCK", reason="situation_not_meet_criteria")
                logger.warning(f"[Safety Net] Situation doesn't meet criteria, blocking S2→S3")
                coach_message = guidance
                internal_state["current_step"] = "S2"  # Stay in S2
        t12 = time.time()
        if old_step == "S2" and new_step == "S3":
            logger.info(f"[PERF] S2 validation: {(t12-t11)*1000:.0f}ms")
        
        # 7. Safety Net: Validate stage transition
        t13 = time.time()
        is_valid, correction = validate_stage_transition(
            old_step, new_step, state, language, coach_message, user_message=user_message
        )
        t14 = time.time()
        logger.info(f"[PERF] Stage transition validation: {(t14-t13)*1000:.0f}ms")
        if old_step != new_step:
            _bsd_log("TRANSITION_ATTEMPT", old_step=old_step, new_step=new_step, allowed=is_valid)

        if not SAFETY_NET_DISABLED and not is_valid and correction:
            overrides_applied.append("transition_block")
            _bsd_log("TRANSITION_BLOCK", old_step=old_step, new_step=new_step, reason=correction[:80])
            logger.warning(f"[Safety Net] Overriding transition {old_step}→{new_step}")
            coach_message = correction
            # Keep current step (don't advance)
            internal_state["current_step"] = old_step
        
        # 6b. Replace placeholder [נושא] in coach_message with actual topic
        topic_for_msg = _safe_get_topic_from_collected(internal_state.get("collected_data"))
        if topic_for_msg and ("[" in topic_for_msg or topic_for_msg.strip() in ("[נושא]", "[topic]")):
            topic_for_msg = ""
        if "[נושא]" in coach_message or "[topic]" in coach_message:
            # Don't use meta-questions (הסביר, מה חסר) or greetings as topic - extract from history
            meta_patterns = ("הסביר", "מה חסר", "מה כוונתך", "לא הבנתי", "מה כוונה", "can you explain", "what do you mean")
            skip_for_topic = ("מה שמך", "שלום", "היי", "what's your name", "hello", "hi")
            is_meta = user_message and any(p in (user_message or "").lower() for p in meta_patterns)
            if not topic_for_msg:
                for msg in reversed(state.get("messages", [])):
                    if isinstance(msg, dict) and msg.get("sender") == "user":
                        c = (msg.get("content") or "").strip()
                        if c and len(c) >= 10 and not any(p in c.lower() for p in meta_patterns) and not any(s in c.lower() for s in skip_for_topic):
                            topic_for_msg = c[:50] + "..." if len(c) > 50 else c
                            break
            replacement = topic_for_msg or ((user_message[:50] + "..." if len(user_message) > 50 else user_message) if user_message and not is_meta and len((user_message or "").strip()) >= 10 else "הנושא")
            coach_message = coach_message.replace("[נושא]", replacement).replace("[topic]", replacement)
        
        # 7. Update state
        logger.info(f"[BSD V2] Parsed coach_message: {coach_message[:100]}...")
        logger.info(f"[BSD V2] Parsed internal_state: {json.dumps(internal_state, ensure_ascii=False)[:200]}...")
        
        # Add user message
        state = add_message(state, "user", user_message)
        
        # Add coach message with internal state
        state = add_message(state, "coach", coach_message, internal_state)
        
        end_time = time.time()
        total_ms = (end_time - start_time) * 1000
        
        logger.info(f"[BSD V2] Updated to step: {state['current_step']}, saturation: {state['saturation_score']:.2f}")
        logger.info(f"[BSD V2] Total messages now: {len(state['messages'])}")
        logger.info(f"[PERF] ⏱️  TOTAL TIME: {total_ms:.0f}ms ({total_ms/1000:.1f}s)")
        _bsd_log("TURN_END", final_step=state['current_step'], overrides=overrides_applied,
                 collected_data_keys=[k for k, v in _safe_collected_dict(state.get('collected_data')).items() if v])

        return coach_message, state
        
    except Exception as e:
        logger.error(f"[BSD V2] Error handling conversation: {e}")
        import traceback
        traceback.print_exc()

        # Graceful fallback for provider rate limiting
        err_text = str(e)
        if "RateLimitReached" in err_text or "Error code: 429" in err_text or "429" in err_text:
            if language == "he":
                return "יש כרגע עומס רגעי במערכת. ננסה שוב בעוד כמה שניות ונמשיך מאותה נקודה.", state
            return "There is temporary load on the model right now. Please retry in a few seconds and we will continue from the same point.", state

        # Generic fallback
        if language == "he":
            fallback = "מצטער, היתה בעיה טכנית. האם נוכל לנסות שוב?"
        else:
            fallback = "Sorry, there was a technical issue. Can we try again?"

        return fallback, state
