"""
Opener Generator - Dynamic, natural coach response openers.

Purpose: Eliminate robotic "שמעתי אותך" by generating contextual, varied openers.

Architecture:
1. LLM generates short, natural opener (0-1 lines)
2. Hard rules enforce quality (length, no repetition, reflection-only)
3. Not mandatory (advance often doesn't need opener)

Schema:
{
  "use_opener": true/false,
  "opener": "short reflection text",
  "style_tag": "reflective"
}
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from .llm import get_azure_chat_llm

logger = logging.getLogger(__name__)


@dataclass
class OpenerResult:
    """Result from opener generation."""
    use_opener: bool
    opener: str
    style_tag: str


# ==========================================
# HARD RULES (Prevent Robotics)
# ==========================================

def _word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def _is_too_similar(opener: str, recent_openers: List[str]) -> bool:
    """
    Check if opener is too similar to recent openers.
    
    Simple heuristic: if >60% of words overlap, it's too similar.
    """
    if not recent_openers:
        return False
    
    opener_words = set(opener.lower().split())
    
    for recent in recent_openers[-3:]:  # Check last 3 openers
        recent_words = set(recent.lower().split())
        
        if not opener_words or not recent_words:
            continue
        
        # Calculate overlap
        overlap = len(opener_words & recent_words)
        total = len(opener_words)
        
        if overlap / total > 0.6:  # 60% overlap
            return True
    
    return False


def _is_interpretation(opener: str) -> bool:
    """
    Check if opener contains interpretation (not pure reflection).
    
    Interpretation markers: Adding emotions/thoughts the user didn't say,
    or making assumptions about their inner state.
    """
    interpretation_markers = [
        # Direct interpretation phrases
        "נראה ש", "נראה לי", "אני חושב", "אני מרגיש",
        "זה אומר", "זה מצביע", "זה מעיד",
        "it seems", "i think", "i feel", "this means", "this suggests",
        
        # Emotion attribution (assuming emotions user didn't say)
        "הרגשת", "הרגשת ש", "היה לך", "התעורר בך",
        "you felt", "you were feeling", "you must have felt",
        
        # Causal interpretation
        "בגלל ש", "כי", "מפני ש", "זה גרם ל",
        "because", "that caused", "which made you",
        
        # Inner state assumptions
        "רצית ש", "חשבת ש", "ציפית ש",
        "you wanted", "you thought", "you expected"
    ]
    
    opener_lower = opener.lower()
    return any(marker in opener_lower for marker in interpretation_markers)


def _is_emotion_list_format(text: str, language: str) -> bool:
    """
    Check if text follows emotion list format.
    
    Expected formats:
    - Hebrew: "אני שומע: X, Y, Z."
    - English: "I hear: X, Y, Z."
    """
    text_lower = text.lower().strip()
    
    if language == "he":
        return text_lower.startswith("אני שומע:") or text_lower.startswith("שמעתי:")
    else:
        return text_lower.startswith("i hear:") or text_lower.startswith("i heard:")


def _enforce_rules(
    opener_result: OpenerResult,
    recent_openers: List[str],
    is_advance: bool,
    stage: str = "",
    language: str = "he"
) -> OpenerResult:
    """
    Enforce hard rules on opener.
    
    Rules:
    1. Length: max 20 words (increased from 12 for richer expression)
    2. No repetition: not too similar to recent openers
    3. No interpretation: reflection-only
    4. Not mandatory: if advance, can skip opener (EXCEPT S3!)
    5. S3 special: must be emotion list format OR event reflection
    6. S1 special: NEVER use opener (no context yet!)
    
    Returns:
        Potentially modified OpenerResult (may disable opener if violates rules)
    """
    # Rule -1: S1 NEVER uses opener (first stage after consent, no context yet!)
    if stage == "S1" and is_advance:
        return OpenerResult(use_opener=False, opener="", style_tag="")
    
    # Rule 0: If advance and no strong need, can skip opener
    # EXCEPTION: S3 always needs opener (to reflect the event)
    if is_advance and not opener_result.use_opener and stage != "S3":
        return opener_result
    
    # S3 MANDATORY: If S3 and no opener, force a generic one
    if stage == "S3" and not opener_result.use_opener:
        logger.info("S3 requires opener, but LLM didn't provide one - using fallback")
        # Don't force - let it through without opener for now
        # The script will guide the user anyway
        return opener_result
    
    # Rule S3: For S3 (Emotion Screen), enforce emotion list format
    if stage == "S3" and opener_result.use_opener:
        # Check if it's a proper emotion list format
        # If not, disable opener (better no opener than wrong format)
        if not _is_emotion_list_format(opener_result.opener, language):
            logger.warning(f"S3 opener not in emotion list format, disabling: '{opener_result.opener[:50]}'")
            return OpenerResult(use_opener=False, opener="", style_tag="")
    
    # Rule 1: Max 20 words (increased for richer expression)
    if _word_count(opener_result.opener) > 20:
        logger.warning(f"Opener too long ({_word_count(opener_result.opener)} words), truncating")
        words = opener_result.opener.split()[:20]
        opener_result.opener = " ".join(words)
    
    # Rule 2: No repetition
    if _is_too_similar(opener_result.opener, recent_openers):
        logger.warning(f"Opener too similar to recent openers, disabling")
        return OpenerResult(use_opener=False, opener="", style_tag="")
    
    # Rule 3: No interpretation
    if _is_interpretation(opener_result.opener):
        logger.warning(f"Opener contains interpretation, disabling")
        return OpenerResult(use_opener=False, opener="", style_tag="")
    
    return opener_result


# ==========================================
# LLM GENERATION
# ==========================================

async def _generate_opener_llm(
    *,
    user_message: str,
    language: str,
    stage: str,
    is_advance: bool,
    critique: str,
    cognitive_data: Dict[str, Any] = None,
    user_gender: str = None
) -> OpenerResult:
    """
    Use LLM to generate a natural opener.
    
    Args:
        user_message: What the user said
        language: "he" or "en"
        stage: Current BSD stage
        is_advance: True if advancing to next stage
        critique: Context about the turn
        cognitive_data: Accumulated session data (topic, emotions, etc.)
    
    Returns:
        OpenerResult with use_opener, opener, style_tag
    """
    cognitive_data = cognitive_data or {}
    llm = get_azure_chat_llm(purpose="talker")  # Warmer temp for natural language
    
    # Special case: S3 (Emotion Screen) - list emotions only, no sentences
    if stage == "S3":
        sys = SystemMessage(content=(
            "You are a BSD coach opener generator for EMOTION SCREEN (S3).\n"
            "Your job: create a SHORT acknowledgment that lists ONLY the emotions the user mentioned.\n"
            "\n"
            "CRITICAL RULES FOR S3:\n"
            "1. LIST EMOTIONS ONLY - no sentences, no explanations\n"
            "2. Format (Hebrew): 'אני שומע: X, Y, Z.'\n"
            "3. Format (English): 'I hear: X, Y, Z.'\n"
            "4. USE EXACT WORDS the user said - don't translate or interpret!\n"
            "5. If user said 'מעצבן', write 'מעצבן', NOT 'תסכול' or 'כעס'\n"
            "6. DO NOT add context or descriptions\n"
            "7. DO NOT write full sentences about what happened\n"
            "\n"
            "✅ GOOD Examples (Hebrew):\n"
            "- User: 'כעס, בושה' → 'אני שומע: כעס, בושה.'\n"
            "- User: 'תסכול יאוש' → 'אני שומע: תסכול, יאוש.'\n"
            "- User: 'מעצבן' → 'אני שומע: מעצבן.' (exact word!)\n"
            "\n"
            "❌ BAD Examples (Hebrew):\n"
            "- User: 'מעצבן' → 'אני שומע: תסכול, כעס.' ← Translation! Use user's words!\n"
            "- 'הבנתי. ביקשת מהילדה לשטוף כלים...' ← Full sentence!\n"
            "\n"
            "✅ GOOD Examples (English):\n"
            "- User: 'anger, shame' → 'I hear: anger, shame.'\n"
            "- User: 'frustrated' → 'I hear: frustrated.' (exact word!)\n"
            "\n"
            "❌ BAD Examples (English):\n"
            "- User: 'annoyed' → 'I hear: anger, frustration.' ← Translation! Use user's words!\n"
            "\n"
            "Return ONLY valid JSON:\n"
            '{"use_opener": true, "opener": "אני שומע: X, Y.", "style_tag": "emotion_list"}\n'
        ))
        
        # Add gender adaptation for S3
        if language == "he" and user_gender:
            gender_note = ""
            if user_gender == "male":
                gender_note = "\nUser is MALE. Use 'אני שומע' (not 'אני שומעת')."
            elif user_gender == "female":
                gender_note = "\nUser is FEMALE. Use 'אני שומעת' (not 'אני שומע')."
            if gender_note:
                sys = SystemMessage(content=sys.content + gender_note)
    else:
        sys = SystemMessage(content=(
            "You are a BSD coach opener generator.\n"
            "Your job: create a NATURAL opening line (1-2 sentences) before the stage prompt.\n"
            "\n"
            "CRITICAL RULES:\n"
            "1. REFLECTION-ONLY: Mirror EXACTLY what the user said, word-for-word when possible.\n"
            "2. NO INTERPRETATION: Don't add emotions, thoughts, or meanings the user didn't say.\n"
            "3. NO ASSUMPTIONS: Don't say 'you felt X' unless they literally said they felt X.\n"
            "4. NATURAL LENGTH: 1-2 sentences, up to 20 words. Use your judgment.\n"
            "5. VARIED: Don't always use 'I hear you' or 'I understand'. Be creative.\n"
            "6. HUMAN: Sound warm and present, not robotic.\n"
            "7. S3 SPECIAL: ALWAYS use opener to reflect the event (mandatory!)\n"
            "\n"
            "✅ GOOD Examples (Hebrew - pure reflection):\n"
            "- 'ביקשת מהילדה לשטוף כלים, היא התמהמהה, צעקת עליה, והיא הלכה לחדר.'\n"
            "- 'היה בלאגן אתמול עם הילדים.'\n"
            "- 'אשתך יצאה לפגוש את אמא שלה ואמרת לה שזה חסר אחריות.'\n"
            "\n"
            "❌ BAD Examples (Hebrew - interpretation!):\n"
            "- 'זה נשמע כמו רגע מורכב שבו הרגשת תסכול.' ← Adding emotion!\n"
            "- 'הרגשת שאין לך שליטה.' ← User didn't say this!\n"
            "- 'זה היה קשה בשבילך.' ← Interpretation of difficulty!\n"
            "\n"
            "✅ GOOD Examples (English):\n"
            "- 'You asked your daughter to wash dishes, she hesitated, you yelled, and she went to her room.'\n"
            "- 'There was chaos yesterday with the kids.'\n"
            "\n"
            "❌ BAD Examples (English):\n"
            "- 'That sounds like a frustrating moment.' ← Adding emotion!\n"
            "- 'You felt out of control.' ← User didn't say this!\n"
            "\n"
            "Return ONLY valid JSON:\n"
            '{"use_opener": true/false, "opener": "text or empty", "style_tag": "reflective"}\n'
        ))
        
        # Add gender adaptation for general stages
        if language == "he" and user_gender:
            gender_note = ""
            if user_gender == "male":
                gender_note = (
                    "\nGENDER: User is MALE. Use MALE forms:\n"
                    "- Use 'אתה' (not 'את')\n"
                    "- Use masculine verbs (e.g., 'ביקשת', not 'ביקשת')\n"
                )
            elif user_gender == "female":
                gender_note = (
                    "\nGENDER: User is FEMALE. Use FEMALE forms:\n"
                    "- Use 'את' (not 'אתה')\n"
                    "- Use feminine verbs (e.g., 'ביקשת', 'הלכת')\n"
                )
            if gender_note:
                sys = SystemMessage(content=sys.content + gender_note)
    
    context = f"Stage: {stage}\n"
    if is_advance:
        # Special case: S3 ALWAYS needs opener (to reflect the event from S2)
        if stage == "S3":
            context += "Action: Advancing to S3 (MUST use opener to reflect the event)\n"
        # Special case: S1 NEVER needs opener (first stage after consent, no context yet)
        elif stage == "S1":
            context += "Action: Advancing to S1 (NO opener - no context yet, go straight to script)\n"
        else:
            context += "Action: Advancing to next stage (opener often not needed)\n"
    else:
        context += "Action: Looping in same stage (opener can help)\n"
    
    if critique:
        context += f"Context: {critique}\n"
    
    # Add cognitive context (what we know so far)
    if cognitive_data:
        context_summary = []
        if cognitive_data.get("topic"):
            context_summary.append(f"Topic: {cognitive_data['topic']}")
        
        event_actual = cognitive_data.get("event_actual", {})
        if event_actual.get("emotions_list"):
            emotions_str = ", ".join(event_actual["emotions_list"][:4])  # First 4
            context_summary.append(f"Emotions so far: {emotions_str}")
        
        if context_summary:
            context += "\nSession context:\n" + "\n".join(context_summary) + "\n"
    
    human = HumanMessage(content=(
        f"Language: {language}\n"
        f"{context}"
        f"User message: {user_message}\n\n"
        "Generate opener (or decide not to use one)."
    ))
    
    try:
        resp = await llm.ainvoke([sys, human])
        text = (resp.content or "").strip()
        
        # Parse JSON
        data = json.loads(text)
        
        return OpenerResult(
            use_opener=bool(data.get("use_opener", False)),
            opener=(data.get("opener") or "").strip(),
            style_tag=(data.get("style_tag") or "reflective").strip()
        )
    
    except Exception as e:
        logger.error(f"Opener generation failed: {e}")
        # Fail-safe: no opener
        return OpenerResult(use_opener=False, opener="", style_tag="")


# ==========================================
# PUBLIC API
# ==========================================

async def generate_opener(
    *,
    user_message: str,
    language: str,
    stage: str,
    is_advance: bool,
    critique: str,
    recent_openers: List[str] = None,
    cognitive_data: Dict[str, Any] = None,
    user_gender: str = None
) -> OpenerResult:
    """
    Generate a natural, non-robotic opener for coach response.
    
    Process:
    1. LLM generates candidate opener
    2. Hard rules enforce quality
    3. Return final opener (or no opener)
    
    Args:
        user_message: What the user said
        language: "he" or "en"
        stage: Current BSD stage
        is_advance: True if advancing to next stage
        critique: Context about the turn
        recent_openers: List of recent openers (for repetition check)
        cognitive_data: Accumulated session data for richer context
    
    Returns:
        OpenerResult with use_opener, opener, style_tag
    """
    recent_openers = recent_openers or []
    
    # Early exit: S1 NEVER uses opener when advancing (save LLM call!)
    if stage == "S1" and is_advance:
        logger.info("[OPENER] S1 advance - skipping opener generation (no context yet)")
        return OpenerResult(use_opener=False, opener="", style_tag="")
    
    # Step 1: LLM generates opener
    result = await _generate_opener_llm(
        user_message=user_message,
        language=language,
        stage=stage,
        is_advance=is_advance,
        critique=critique,
        user_gender=user_gender,
        cognitive_data=cognitive_data
    )
    
    # Step 2: Enforce hard rules
    result = _enforce_rules(result, recent_openers, is_advance, stage, language)
    
    # Log result
    if result.use_opener:
        logger.info(f"Generated opener ({_word_count(result.opener)} words): '{result.opener[:50]}...'")
    else:
        logger.info("No opener used (advance or rules violation)")
    
    return result


# Public API
__all__ = ["generate_opener", "OpenerResult"]

