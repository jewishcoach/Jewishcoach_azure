from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import json
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from .llm import get_azure_chat_llm
from .stage_defs import StageId, next_stage

"""
BSD Reasoner (Gatekeeper) - Enterprise-grade validation and decision logic.

The Reasoner decides whether to advance to the next stage or loop for more information.
It operates invisibly to the user and enforces strict methodology gates.
"""

logger = logging.getLogger(__name__)


async def classify_s0_intent(*, user_message: str, language: str) -> dict:
    """
    Intent classifier for S0 (permission step).
    
    Classifies user message into one of:
    - CONSENT_YES: explicit permission to start
    - CONSENT_NO: explicit refusal
    - CLARIFY: user asks what this means / how it works
    - TOPIC_OR_SMALLTALK: user provides topic or answers smalltalk
    
    Returns:
        dict with keys: intent, confidence, topic_candidate
    """
    msg_lower = user_message.lower().strip()
    
    # LAYER 1: DETERMINISTIC RULES (faster, more reliable)
    
    # Check for explicit consent (YES patterns)
    consent_yes_he = ["כן", "בטח", "כמובן", "יש לך רשות", "אשמח", "בוא", "בואו", "בואי", "המשך", "המשיכו", "המשיכי"]
    consent_yes_en = ["yes", "sure", "of course", "you have permission", "i'd love to", "let's do it", "go ahead", "continue"]
    
    consent_patterns = consent_yes_he if language == "he" else consent_yes_en
    if any(pattern in msg_lower for pattern in consent_patterns):
        # Explicit consent detected
        logger.info(f"[S0 CLASSIFIER] CONSENT_YES detected (deterministic)")
        return {
            "intent": "CONSENT_YES",
            "confidence": 0.95,
            "topic_candidate": ""
        }
    
    # Check for explicit refusal (NO patterns)
    consent_no_he = ["לא", "לא רוצה", "לא מעוניין", "תודה לא", "לא צריך"]
    consent_no_en = ["no", "don't want", "not interested", "no thanks", "don't need"]
    
    refusal_patterns = consent_no_he if language == "he" else consent_no_en
    if any(pattern in msg_lower for pattern in refusal_patterns) and len(msg_lower) < 30:
        # Explicit refusal detected
        logger.info(f"[S0 CLASSIFIER] CONSENT_NO detected (deterministic)")
        return {
            "intent": "CONSENT_NO",
            "confidence": 0.95,
            "topic_candidate": ""
        }
    
    # Check for clarification questions
    if "?" in user_message:
        logger.info(f"[S0 CLASSIFIER] CLARIFY detected (question mark)")
        return {
            "intent": "CLARIFY",
            "confidence": 0.9,
            "topic_candidate": ""
        }
    
    # LAYER 2: LLM CLASSIFIER (only if deterministic rules didn't match)
    logger.info(f"[S0 CLASSIFIER] Using LLM for: '{user_message}'")
    
    llm = get_azure_chat_llm(purpose="reasoner")  # cold

    sys = SystemMessage(content=(
        "You are an intent classifier for the FIRST step of a BSD coaching flow (permission step).\n"
        "Classify the user's message into exactly ONE of:\n"
        "CONSENT_YES, CONSENT_NO, CLARIFY, TOPIC_OR_SMALLTALK.\n"
        "Return ONLY valid JSON with keys: intent, confidence, topic_candidate.\n"
        "\n"
        "Rules:\n"
        "- CONSENT_YES: explicit permission to start (e.g., 'yes', 'sure', 'let's start').\n"
        "- CONSENT_NO: explicit refusal (e.g., 'no', 'not now').\n"
        "- CLARIFY: user asks what this means / what to start / how it works.\n"
        "- TOPIC_OR_SMALLTALK: user provides a topic (e.g., 'parenting', 'work stress') OR answers smalltalk.\n"
        "\n"
        "CRITICAL: If user gives a short statement that could be a topic (1-3 words), classify as TOPIC_OR_SMALLTALK, NOT CLARIFY!\n"
        "Examples of TOPIC_OR_SMALLTALK: 'עמידה ביעדים', 'parenting', 'work stress', 'anger at kids'\n"
        "\n"
        "If unsure between CONSENT_YES and TOPIC_OR_SMALLTALK, choose TOPIC_OR_SMALLTALK."
    ))

    human = HumanMessage(content=f"Language: {language}\nUser message: {user_message}")

    try:
        resp = await llm.ainvoke([sys, human])
        text = (resp.content or "").strip()
        
        data = json.loads(text)
        if data.get("intent") not in {"CONSENT_YES", "CONSENT_NO", "CLARIFY", "TOPIC_OR_SMALLTALK"}:
            raise ValueError("bad intent")
        
        logger.info(f"[S0 CLASSIFIER] LLM result: {data['intent']} (confidence={data.get('confidence', 0.5)})")
        
        return {
            "intent": data["intent"],
            "confidence": float(data.get("confidence", 0.5)),
            "topic_candidate": (data.get("topic_candidate") or "").strip()
        }
    except Exception as e:
        logger.error(f"[S0 CLASSIFIER] LLM error: {e}")
        # fail closed: if short message, likely a topic; otherwise clarify
        if len(user_message.split()) <= 5 and "?" not in user_message:
            return {"intent": "TOPIC_OR_SMALLTALK", "confidence": 0.4, "topic_candidate": user_message.strip()}
        return {"intent": "CLARIFY", "confidence": 0.3, "topic_candidate": ""}


def _get_gate_instructions(stage: StageId, language: str) -> str:
    """
    Get gate conditions for a stage in the specified language.
    
    These are short, explicit instructions that the LLM uses to validate
    whether the user has satisfied the stage requirements.
    """
    he = {
        StageId.S0: "נדרש אישור מפורש להתחיל תהליך (כן/בטח/מאשר). ברכה בלבד אינה מספיקה.",
        StageId.S1: "LENIENT: קבל כמעט כל דבר כנושא! ✓ 'היכולת שלי להצליח בעסקים' ✓ 'הובלת פרויקטים' ✓ 'רומנטיות' ✓ 'קבלת החלטות' ✓ כל אתגר/כישור/תחום. דחה רק: ❌ 'לא יודע' ❌ שאלות ❌ סירוב.",
        StageId.S2: "נדרש אירוע ספציפי לאחרונה עם רגש חזק ואנשים נוספים מעורבים.",
        StageId.S2_READY: "CRITICAL: בדיקת נכונות (3 שאלות). אם המשתמש אומר 'לא מסוגל' או 'אין לי כוח' → STOP! אחרת → ADVANCE.",
        StageId.S3: "נדרשים לפחות 4 רגשות שונים.",
        StageId.S4: "LENIENT: כל משפט/מחשבה שמבטא דעה על עצמו/מצב → ADVANCE. דוגמאות: 'אני אפס', 'זה לא הוגן', 'אני לא מספיק טוב'. אל תדרוש 'איכות' - רק שיש משהו.",
        StageId.S5: "LENIENT: כל תיאור של מה עשה/לא עשה → ADVANCE. דוגמאות: 'סגרתי את המחשב', 'צעקתי', 'שתקתי'. לא צריך פירוט מלא.",
        StageId.S6: "נדרש שם לפער + ציון 1–10.",
        StageId.S7: "LENIENT: כל תיאור של דפוס חוזר או אמונה → ADVANCE. לא צריך ניתוח מושלם.",
        StageId.S8: "MODERATE: נדרש זיהוי רווח והפסד מהעמדה. דוגמה: 'אני מרוויח ביטחון אבל מפסיד קרבה'. אם יש תיאור של שניהם → ADVANCE.",
        StageId.S9: "LENIENT: כל רשימה של כוחות/משאבים → ADVANCE. לא צריך הבחנה מושלמת בין מקור לטבע.",
        StageId.S11: "MODERATE: נדרש תיאור של בחירה חדשה (עמדה/פרדיגמה/דפוס). אם יש לפחות אחד מהם → ADVANCE.",
        StageId.S12: "LENIENT: כל תיאור של חזון/שליחות/יעוד → ADVANCE. לא צריך פילוסופיה מושלמת.",
        StageId.S10: "נדרש ניסוח בקשת אימון מלאה לפי הנוסחה.",
    }
    en = {
        StageId.S0: "User must give explicit consent to start (yes/ok/I agree). Greeting alone is not enough.",
        StageId.S1: "LENIENT: Accept almost anything as a topic! ✓ 'my ability to succeed in business' ✓ 'project leadership' ✓ 'romance' ✓ 'decision making' ✓ ANY challenge/skill/area. Reject only: ❌ 'I don't know' ❌ questions ❌ refusal.",
        StageId.S2: "User must describe one specific recent event with strong emotion and other people involved.",
        StageId.S2_READY: "CRITICAL: Readiness check (3 questions). If user says 'I can't' or 'I'm not capable' → STOP! Otherwise → ADVANCE.",
        StageId.S3: "User must list at least 4 distinct emotions.",
        StageId.S4: "LENIENT: ANY sentence expressing thought/opinion about self/situation → ADVANCE. Examples: 'I'm worthless', 'It's unfair', 'I'm not good enough'. Don't judge quality.",
        StageId.S5: "LENIENT: ANY description of what they did/didn't do → ADVANCE. Examples: 'closed laptop', 'yelled', 'stayed silent'. No need for full detail.",
        StageId.S6: "User must name the gap and rate 1–10.",
        StageId.S7: "LENIENT: ANY description of recurring pattern or belief → ADVANCE. Don't need perfect analysis.",
        StageId.S8: "MODERATE: User must identify profit AND loss from their stance. Example: 'I gain security but lose intimacy'. If both described → ADVANCE.",
        StageId.S9: "LENIENT: ANY list of forces/resources → ADVANCE. Don't need perfect distinction between source and nature.",
        StageId.S11: "MODERATE: User must describe new choice (stance/paradigm/pattern). If at least one is described → ADVANCE.",
        StageId.S12: "LENIENT: ANY description of vision/mission/destiny → ADVANCE. No perfect philosophy needed.",
        StageId.S10: "User completes the commitment formula.",
    }
    return (he if language == "he" else en).get(stage, "Use judgment; if unsure, LOOP.")


@dataclass
class ReasonerDecision:
    """
    Enterprise Decision output from the Reasoner/Router.
    
    Attributes:
        intent: User's intent classification (ANSWER_OK|ANSWER_PARTIAL|CLARIFY|OFFTRACK|ADVICE_REQUEST|STOP)
        decision: Action to take (advance|loop|stop)
        next_stage: Stage ID if advancing, None if looping/stopping
        reasons: List of reasons for the decision (for audit)
        extracted: Structured data extracted from user input (emotions, thoughts, etc.)
        missing: What's missing to complete the stage (count/fields)
        critique: Hidden instructions for the Talker (short hint)
        repair_intent: Generic repair intent from Generic Critique Detector (e.g. ASK_EXAMPLE, ENCOURAGE_TRY)
        generic_critique_label: Label from Generic Critique (e.g. TOO_VAGUE, AVOIDANCE)
        generic_critique_confidence: Confidence score (0.0-1.0) from Generic Critique
    """
    intent: str  # ANSWER_OK|ANSWER_PARTIAL|CLARIFY|OFFTRACK|ADVICE_REQUEST|STOP
    decision: str  # advance|loop|stop
    next_stage: Optional[str]
    reasons: List[str]
    extracted: Dict[str, Any]
    missing: Dict[str, Any]
    critique: str
    repair_intent: Optional[str] = None  # e.g. "ASK_EXAMPLE", "ENCOURAGE_TRY", None
    generic_critique_label: Optional[str] = None  # e.g. "TOO_VAGUE", "AVOIDANCE", None
    generic_critique_confidence: Optional[float] = None  # 0.0-1.0


def _simple_emotion_list(text: str) -> List[str]:
    """
    Extract emotions from text using simple heuristics.
    
    Splits on commas, newlines, AND spaces (for Hebrew: "כעס קנאה תסכול").
    Filters out common thought patterns (e.g., "אני אבא גרוע", "I'm a failure").
    Deduplicates while preserving order.
    
    Examples:
        "כעס, קנאה" → ["כעס", "קנאה"]
        "כעס קנאה" → ["כעס", "קנאה"]
        "תסכול, הרגשתי שאני אבא גרוע" → ["תסכול"] (filters thought)
    """
    # CRITICAL: Detect and filter thought patterns BEFORE splitting
    # These are thoughts disguised as emotions
    thought_patterns_he = [
        "אני ", "אנחנו ", "הוא ", "היא ", "הם ", "הן ",
        "את ", "אתה ", "זה ", "זאת ",
        "שאני ", "שהוא ", "שהיא ", "שאתה ", "שאת ",
    ]
    thought_patterns_en = [
        "i am ", "i'm ", "he is ", "she is ", "they are ",
        "you are ", "it is ", "that i ", "that he ", "that she ",
    ]
    
    # Check if text contains thought pattern
    text_lower = text.lower().strip()
    has_thought_pattern = any(pattern in text_lower for pattern in thought_patterns_he + thought_patterns_en)
    
    if has_thought_pattern:
        # This likely contains a thought, not just emotions
        # Extract only the parts BEFORE the thought pattern
        parts = []
        for pattern in thought_patterns_he + thought_patterns_en:
            if pattern in text_lower:
                # Take only the part before the pattern
                idx = text_lower.index(pattern)
                before_pattern = text[:idx].strip()
                if before_pattern:
                    parts.append(before_pattern)
                # Don't include the thought part
                logger.info(f"🧠 [S3 FILTER] Detected thought pattern '{pattern}' - filtering: '{text[idx:]}'")
                text = before_pattern  # Only process the part before the thought
                break
    
    # First, normalize: newlines → commas, then split by commas and spaces
    text = text.replace("\n", ",")
    
    # Split by commas first, then by spaces within each part
    raw_tokens = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        # Split by spaces to catch "תסכול יאוש" style
        raw_tokens.extend([t.strip() for t in part.split() if t.strip()])
    
    # Filter out non-emotion words (verbs, connectors, etc.)
    non_emotion_words = [
        "הרגשתי", "הרגשת", "feeling", "felt", "feel", "שאני", "שהוא", 
        "שהיא", "that", "and", "ו", "או", "or", "גם", "also"
    ]
    raw_tokens = [t for t in raw_tokens if t.lower() not in non_emotion_words]
    
    # Deduplicate while preserving order
    seen, out = set(), []
    for e in raw_tokens:
        if e and e not in seen:
            seen.add(e)
            out.append(e)
    
    logger.info(f"[S3 EXTRACT] Input: '{text[:50]}...' → Emotions: {out}")
    return out


def _coerce_decision(data: dict, *, stage: StageId) -> ReasonerDecision:
    """
    Coerce LLM output into a valid ReasonerDecision.
    
    This ensures that even if the LLM returns malformed data,
    we always get a valid decision object (fail-closed to LOOP).
    """
    # Validate decision
    decision = data.get("decision", "loop")
    if decision not in ("advance", "loop"):
        logger.warning(f"Invalid decision '{decision}', defaulting to 'loop'")
        decision = "loop"

    # Ensure next_stage is set if advancing
    ns = data.get("next_stage")
    if decision == "advance" and not ns:
        ns = next_stage(stage).value if next_stage(stage) else None

    # Coerce reasons to list of strings
    reasons = data.get("reasons") or []
    if not isinstance(reasons, list):
        reasons = [str(reasons)]

    # Ensure extracted is a dict
    extracted = data.get("extracted") or {}
    if not isinstance(extracted, dict):
        logger.warning(f"Invalid extracted type {type(extracted)}, using empty dict")
        extracted = {}

    # Ensure critique is a string
    critique = data.get("critique") or ""
    
    # Intent and missing (may not always be present in LLM response)
    intent = data.get("intent") or ("ANSWER_OK" if decision == "advance" else "ANSWER_PARTIAL")
    missing = data.get("missing") or {}

    return ReasonerDecision(
        intent=intent,
        decision=decision,
        next_stage=ns if decision == "advance" else None,
        reasons=[str(r) for r in reasons],
        extracted=extracted,
        missing=missing,
        critique=str(critique),
    )


async def decide(
    *,
    stage: str | StageId,
    user_message: str,
    language: str,
    state: Any = None,  # BsdState for router
    cognitive_data: Dict[str, Any] | None = None,  # Legacy, kept for compatibility
) -> ReasonerDecision:
    """
    Decide whether to advance to the next stage or loop.
    
    Args:
        stage: Current stage ID
        user_message: User's message to evaluate
        language: "he" or "en"
    
    Returns:
        ReasonerDecision with advance/loop decision and extracted data
    
    The Reasoner uses:
    1. Deterministic rules for critical gates (e.g., S3 >= 4 emotions)
    2. LLM-based semantic validation for other gates
    3. Fail-closed: defaults to LOOP if uncertain
    """
    stg = StageId(stage) if not isinstance(stage, StageId) else stage
    
    # META-DISCUSSION DETECTION: User asking about the process itself
    # These are legitimate clarification questions, not OFFTRACK
    meta_patterns_he = ["איזה שלב", "אנחנו בשלב", "המצוי", "לאן הולכים", "מה הבא", "איפה אנחנו"]
    meta_patterns_en = ["what stage", "which phase", "where are we", "what's next", "current stage"]
    meta_patterns = meta_patterns_he if language == "he" else meta_patterns_en
    
    user_lower = user_message.lower()
    if any(pattern in user_lower for pattern in meta_patterns):
        logger.info(f"[REASONER {stg.value}] META-DISCUSSION detected - user asking about process")
        return ReasonerDecision(
            intent="META_DISCUSSION",
            decision="loop",
            next_stage=None,
            reasons=["User asking about the coaching process itself."],
            extracted={},
            missing={},
            critique="META_DISCUSSION",
        )

    # S0 Intent Router - classify user intent with LLM
    if stg == StageId.S0:
        intent = await classify_s0_intent(user_message=user_message, language=language)
        
        logger.info(f"[REASONER S0] Intent classified: {intent['intent']} (confidence: {intent['confidence']})")

        if intent["intent"] == "CONSENT_YES":
            return ReasonerDecision(
                intent="ANSWER_OK",
                decision="advance",
                next_stage=next_stage(stg).value if next_stage(stg) else None,
                reasons=["Explicit consent detected."],
                extracted={},
                missing={},
                critique=""
            )

        if intent["intent"] == "CONSENT_NO":
            return ReasonerDecision(
                intent="STOP",
                decision="loop",
                next_stage=None,
                reasons=["User refused consent."],
                extracted={},
                missing={},
                critique="S0_STOP"
            )

        if intent["intent"] == "CLARIFY":
            return ReasonerDecision(
                intent="CLARIFY",
                decision="loop",
                next_stage=None,
                reasons=["User asked clarification."],
                extracted={},
                missing={},
                critique="S0_CLARIFY"
            )

        # TOPIC_OR_SMALLTALK
        return ReasonerDecision(
            intent="OFFTRACK",
            decision="loop",
            next_stage=None,
            reasons=["User provided topic/smalltalk instead of consent."],
            extracted={"topic_candidate": intent["topic_candidate"]},
            missing={},
            critique="S0_REDIRECT_TO_CONSENT"
        )

    # Deterministic gate: S1 must have a topic (ULTRA-LENIENT - accept EVERYTHING except explicit refusal)
    if stg == StageId.S1:
        user_lower = user_message.lower().strip()
        word_count = len(user_message.split())
        
        # REJECT only if EXPLICIT refusal or "I don't know"
        # Changed: Accept even 1-word topics! ("רומנטיקה", "עבודה", etc.)
        explicit_refusal_he = ["לא רוצה", "אין לי נושא", "לא יודע מה", "ממש לא יודע"]
        explicit_refusal_en = ["don't want to", "no topic", "don't know what", "really don't know"]
        explicit_refusal = explicit_refusal_he if language == "he" else explicit_refusal_en
        
        # Only reject if:
        # 1. Explicit "I don't know" (2+ words containing "לא יודע"/"don't know")
        # 2. Explicit refusal
        # 3. Just a question mark
        is_dont_know = any(pattern in user_lower for pattern in ["לא יודע", "don't know", "אין מושג", "no idea"])
        is_refusal = any(pattern in user_lower for pattern in explicit_refusal)
        is_just_question = user_message.strip() == "?"
        
        if (is_dont_know or is_refusal or is_just_question):
            logger.info(f"🔁 [REASONER S1] LOOP - explicit refusal/don't know: '{user_message}'")
            return ReasonerDecision(
                intent="CLARIFY",
                decision="loop",
                next_stage=None,
                reasons=["User doesn't know or refused to provide topic."],
                extracted={},
                missing={"topic": True},
                critique="S1_CLARIFY",
            )
        
        # ACCEPT EVERYTHING ELSE! (even 1 word, even "broad" topics)
        # "רומנטיקה" ✓ "עבודה" ✓ "הצלחה בעסקים" ✓ "היכולת שלי ל..." ✓
        logger.info(f"✅ [REASONER S1] ULTRA-LENIENT PASS - accepting '{user_message[:40]}...' as topic")
        return ReasonerDecision(
            intent="ANSWER_OK",
            decision="advance",
            next_stage=next_stage(stg).value if next_stage(stg) else None,
            reasons=[f"Topic provided (ultra-lenient): '{user_message[:50]}'"],
            extracted={"topic": user_message},
            missing={},
            critique="",
        )
    
    # S2 GATE: Use LLM to judge if event is specific enough
    # This is BETTER than deterministic patterns because it's generic and catches nuance
    if stg == StageId.S2:
        logger.info(f"[S2 GATE] Evaluating event specificity via LLM for: '{user_message[:80]}...'")
        
        # Use LLM to judge specificity
        judge_prompt = f"""You are evaluating if a user's response describes a SPECIFIC EVENT or just a general situation.

User said: "{user_message}"

A SPECIFIC EVENT must include:
1. A concrete moment in time (when exactly?)
2. What actually happened (specific actions, not "it was bad")
3. Enough detail to visualize the scene

Examples of SPECIFIC:
✓ "אתמול בערב יצאתי עם מישהי לבית קפה והתרגשתי כל כך שדיברתי שטויות"
✓ "Yesterday I told my boss I needed help and he ignored me"

Examples of NOT SPECIFIC:
✗ "בשבוע האחרון לא יצאתי עם מישהי" (didn't happen)
✗ "יצאתי שבוע לפני והיה נורא" (vague, no detail)
✗ "אני לא מצליח למצוא זוגיות" (general situation)
✗ "יש לי פרויקט שאני עובד עליו" (general, not a moment)

Respond ONLY with valid JSON:
{{"is_specific": true/false, "reason": "brief explanation"}}"""

        try:
            llm = get_chat_llm(temperature=0.0, streaming=False)
            response = await llm.ainvoke([
                SystemMessage(content="You are a precise evaluator. Output only valid JSON."),
                HumanMessage(content=judge_prompt)
            ])
            
            # Parse LLM response
            import json
            response_text = response.content.strip()
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            is_specific = result.get("is_specific", False)
            reason = result.get("reason", "")
            
            logger.info(f"[S2 GATE LLM] is_specific={is_specific}, reason={reason}")
            
            if not is_specific:
                logger.info(f"🔁 [REASONER S2] LOOP - LLM judged event not specific enough")
                return ReasonerDecision(
                    intent="ANSWER_PARTIAL",
                    decision="loop",
                    next_stage=None,
                    reasons=[f"Event not specific enough: {reason}"],
                    extracted={},
                    missing={"needs": ["specific_event_moment"]},
                    critique="S2_NOT_SPECIFIC",
                )
            
            # PASS: Event is specific enough
            logger.info(f"✅ [REASONER S2] PASS LLM gate - event is specific")
            return ReasonerDecision(
                intent="ANSWER_OK",
                decision="advance",
                next_stage=next_stage(stg).value if next_stage(stg) else None,
                reasons=[f"Event is specific: {reason}"],
                extracted={"event_description": user_message},
                missing={},
                critique="",
            )
            
        except Exception as e:
            logger.error(f"[S2 GATE] LLM failed: {e}, falling back to STRICT mode")
            # Fallback: If LLM fails, require very clear markers
            user_lower = user_message.lower()
            time_markers = ["אתמול", "היום", "אמש", "yesterday", "today", "last night"]
            action_markers = ["אמרתי", "עשיתי", "i said", "i did", "happened"]
            
            has_clear_event = (
                any(m in user_lower for m in time_markers) and 
                any(m in user_lower for m in action_markers) and
                len(user_message.split()) > 12
            )
            
            if not has_clear_event:
                return ReasonerDecision(
                    intent="ANSWER_PARTIAL",
                    decision="loop",
                    next_stage=None,
                    reasons=["Event not clear enough (LLM unavailable, using strict fallback)"],
                    extracted={},
                    missing={"needs": ["specific_event"]},
                    critique="S2_NOT_SPECIFIC",
                )
            
            return ReasonerDecision(
                intent="ANSWER_OK",
                decision="advance",
                next_stage=next_stage(stg).value if next_stage(stg) else None,
                reasons=["Event appears specific (fallback mode)"],
                extracted={},
                missing={},
                critique="",
            )
    
    # Readiness Check (S2_READY) - "Triple Engine" questions
    # Checks if user has: 1) Importance 2) Belief in change 3) Self-efficacy
    if stg == StageId.S2_READY:
        user_lower = user_message.lower().strip()
        
        # Check for explicit "I can't" / "I'm not capable"
        low_belief_he = ["לא מסוגל", "לא יכול", "אין לי כוח", "לא מצליח", "לא חושב שאני", "לא מאמין שאני"]
        low_belief_en = ["i can't", "i'm not capable", "no strength", "not able", "don't think i can", "don't believe i can"]
        low_belief_patterns = low_belief_he if language == "he" else low_belief_en
        
        has_low_self_belief = any(pattern in user_lower for pattern in low_belief_patterns)
        
        if has_low_self_belief:
            logger.info(f"⛔ [REASONER S2_READY] STOP - low self-belief detected: '{user_message}'")
            return ReasonerDecision(
                intent="STOP",
                decision="loop",
                next_stage=None,
                reasons=["User expressed low self-belief - coaching requires existing capacity."],
                extracted={"readiness": "low_self_belief"},
                missing={},
                critique="READINESS_LOW_SELF_BELIEF",
            )
        
        # Check if user answered affirmatively (even partially)
        # We're LENIENT - accept any response that's not explicit "I can't"
        word_count = len(user_message.split())
        
        # Accept if message has substance (>3 words) OR contains positive markers
        positive_markers_he = ["כן", "בטח", "מאמין", "יכול", "מסוגל", "חשוב", "אפשרי", "רוצה"]
        positive_markers_en = ["yes", "sure", "believe", "can", "capable", "important", "possible", "want"]
        positive_markers = positive_markers_he if language == "he" else positive_markers_en
        
        has_positive = any(marker in user_lower for marker in positive_markers)
        
        if word_count >= 3 or has_positive:
            logger.info(f"✅ [REASONER S2_READY] PASS - user ready to proceed: '{user_message}'")
            return ReasonerDecision(
                intent="ANSWER_OK",
                decision="advance",
                next_stage=next_stage(stg).value if next_stage(stg) else None,
                reasons=["User expressed readiness to proceed."],
                extracted={"readiness": "ready"},
                missing={},
                critique="",
            )
        
        # If too short or unclear → LOOP (ask again)
        logger.info(f"🔁 [REASONER S2_READY] LOOP - unclear response: '{user_message}'")
        return ReasonerDecision(
            intent="ANSWER_PARTIAL",
            decision="loop",
            next_stage=None,
            reasons=["Response unclear. Need answers to the 3 readiness questions."],
            extracted={},
            missing={"readiness_answers": True},
            critique="S2_READY_UNCLEAR",
        )
    
    # Deterministic gate: S4 must have a complete thought (sentence)
    if stg == StageId.S4:
        user_trimmed = user_message.strip()
        word_count = len(user_trimmed.split())
        
        # REJECT if:
        # 1. Too short (< 3 words) - "אני לא" is not a complete thought
        # 2. Ends with incomplete marker (e.g., "באמצ" without completing the word)
        # 3. Empty or just a question mark
        
        # Check for incomplete Hebrew words (ends with ב, ל, מ, ש without vowels)
        hebrew_chars = set("אבגדהוזחטיכלמנסעפצקרשתךםןףץ")
        looks_incomplete = False
        if user_trimmed and user_trimmed[-1] in hebrew_chars:
            # Check if last word looks cut off (no space before end)
            words = user_trimmed.split()
            if words:
                last_word = words[-1]
                # Very short last word (1-3 chars) might be incomplete
                if len(last_word) <= 3:
                    looks_incomplete = True
        
        is_too_short = word_count < 3
        is_empty = not user_trimmed or user_trimmed == "?"
        
        if is_empty or is_too_short or looks_incomplete:
            logger.info(f"🔁 [REASONER S4] LOOP - thought incomplete/too short: '{user_message}'")
            return ReasonerDecision(
                intent="ANSWER_PARTIAL",
                decision="loop",
                next_stage=None,
                reasons=["Thought seems incomplete or too short. Need a complete sentence/thought."],
                extracted={},
                missing={"thought": True},
                critique="S4_INCOMPLETE",
            )
        
        # Otherwise, ACCEPT as a thought (LLM will validate content quality)
        logger.info(f"✅ [REASONER S4] PASS gate - thought seems complete: '{user_message[:40]}...'")
        # Don't advance here - let LLM validate it's actually a thought (not emotion/action)
        # Fall through to LLM validation below
    
    # Deterministic gate: S3 must have >=4 emotions (ACCUMULATION across loops!)
    if stg == StageId.S3:
        # Extract existing emotions from cognitive_data (continuity!)
        existing = []
        if cognitive_data:
            event_actual = cognitive_data.get("event_actual", {})
            existing = event_actual.get("emotions_list", [])
        
        # Parse new emotions from current message
        new_emotions = _simple_emotion_list(user_message)
        
        # Merge: unique emotions only (preserve order, deduplicate)
        merged = existing.copy()
        for e in new_emotions:
            if e not in merged:
                merged.append(e)
        
        # Decide based on ACCUMULATED count
        if len(merged) >= 4:
            logger.info(f"✅ [REASONER S3] ADVANCE - accumulated {len(merged)} emotions: {merged}")
            return ReasonerDecision(
                intent="ANSWER_OK",
                decision="advance",
                next_stage=next_stage(stg).value if next_stage(stg) else None,
                reasons=[f"Accumulated {len(merged)} emotion tokens (>=4)."],
                extracted={"emotions_list": merged},  # Return MERGED list
                missing={},
                critique="",
            )
        
        logger.info(
            f"🔁 [REASONER S3] LOOP - accumulated {len(merged)} emotions: {merged}. "
            f"Need {4 - len(merged)} more."
        )
        emotions_str = ", ".join(merged) if merged else "none yet"
        missing = 4 - len(merged)
        
        return ReasonerDecision(
            intent="ANSWER_PARTIAL",
            decision="loop",
            next_stage=None,
            reasons=[f"Only {len(merged)} emotion tokens; need at least 4."],
            extracted={"emotions_list": merged},  # Return accumulated list
            missing={"emotions_needed": missing},
            critique=(
                f"Accumulated {len(merged)} emotion(s): {emotions_str}. "
                f"Need {missing} more emotion{'s' if missing > 1 else ''} to complete the screen."
            ),
        )

    # LLM-based validation for other stages
    llm = get_azure_chat_llm(purpose="reasoner")
    gate_instructions = _get_gate_instructions(stg, language)

    sys = SystemMessage(
        content=(
            "You are the hidden BSD Gatekeeper (Reasoner). You do NOT talk to the user.\n"
            "Your job: Check if user provided MINIMUM required info to pass the gate.\n"
            "\n"
            "CRITICAL PRINCIPLES:\n"
            "1. BE LENIENT - We're checking PRESENCE, not QUALITY\n"
            "2. If user provided SOMETHING relevant → ADVANCE\n"
            "3. Only LOOP if truly missing or off-topic\n"
            "4. Don't judge depth/sophistication - that's not your role\n"
            "\n"
            "Examples of being TOO STRICT (WRONG):\n"
            "❌ Stage S4 (thought): User says 'אני אפס' → DON'T loop asking for 'better' thought\n"
            "❌ Stage S5 (action): User says 'סגרתי את המחשב' → DON'T loop asking for 'more detail'\n"
            "✅ If they gave SOMETHING that fits the category → ADVANCE\n"
            "\n"
            "Return ONLY valid JSON (no markdown, no code blocks).\n"
            "\n"
            "Schema:\n"
            '{\n'
            '  "decision": "advance" | "loop",\n'
            '  "next_stage": "S0" | "S1" | ... | "S10" | null,\n'
            '  "reasons": ["reason 1", "reason 2", ...],\n'
            '  "extracted": { /* any structured data */ },\n'
            '  "critique": "instruction for Talker (if loop)"\n'
            '}\n'
        )
    )
    human = HumanMessage(
        content=(
            f"Stage: {stg.value}\n"
            f"Language: {language}\n"
            f"Gate conditions: {gate_instructions}\n"
            f"User message:\n{user_message}\n"
        )
    )

    try:
        resp = await llm.ainvoke([sys, human])
        text = (resp.content or "").strip()
        
        # Log for debugging (but not print)
        logger.debug(f"Reasoner LLM response for {stg.value}: {text[:200]}...")
        
        # Parse JSON
        data = json.loads(text)
        return _coerce_decision(data, stage=stg)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Reasoner JSON for {stg.value}: {e}")
        # Fail closed: default to LOOP
        return ReasonerDecision(
            intent="CLARIFY",
            decision="loop",
            next_stage=None,
            reasons=["Gatekeeper output was not valid JSON; default LOOP."],
            extracted={},
            missing={},
            critique="Ask one clarifying question aligned to the gate. Do not advance.",
        )
    except Exception as e:
        logger.error(f"Reasoner error for {stg.value}: {e}")
        # Fail closed
        return ReasonerDecision(
            intent="CLARIFY",
            decision="loop",
            next_stage=None,
            reasons=[f"Gatekeeper error: {str(e)[:100]}"],
            extracted={},
            missing={},
            critique="Ask a clarifying question.",
        )


# Public API
__all__ = ["decide", "ReasonerDecision"]
