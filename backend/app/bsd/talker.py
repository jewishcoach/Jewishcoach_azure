from __future__ import annotations

import re
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from .llm import get_azure_chat_llm
from .scripts import get_script, get_loop_prompt, ScriptNotFoundError, adapt_to_gender
from .stage_defs import StageId
from .opener_generator import generate_opener
from .conversational_coach import generate_natural_response
from .knowledge_rag import get_rag_service
import os

"""
BSD Talker - Generates empathetic, methodology-compliant coach responses.

Enterprise behaviors:
- Uses FULL SCRIPT on advance (verbatim)
- Uses SHORT LOOP PROMPT on loop (avoids "broken record")
- Uses DYNAMIC GUIDANCE when repair_intent is provided (LLM-generated, natural)
- Validates input (detects numbers, gibberish)
- Audits verbatim script inclusion
- Falls back gracefully on LLM errors
"""

logger = logging.getLogger(__name__)


async def generate_dynamic_guidance(
    *,
    stage: StageId,
    language: str,
    user_message: str,
    repair_intent: str,
    generic_critique_label: str | None,
    missing: dict | None,
    user_gender: str | None = None,
) -> str:
    """
    Generate dynamic guidance using LLM based on repair_intent from Generic Critique.
    
    This function takes the INTENT of what repair is needed and generates a natural,
    empathetic question/guidance in the user's language.
    
    Args:
        stage: Current coaching stage
        language: "he" or "en"
        user_message: What the user said
        repair_intent: Type of repair needed (ASK_EXAMPLE, ENCOURAGE_TRY, etc.)
        generic_critique_label: The critique label (TOO_VAGUE, AVOIDANCE, etc.)
        missing: What's specifically missing from stage gate
        user_gender: User's gender for language adaptation
    
    Returns:
        Natural, empathetic guidance message
    """
    from .generic_critique import STAGE_REQUIREMENTS
    
    llm = get_azure_chat_llm(purpose="talker")
    
    stage_requirement = STAGE_REQUIREMENTS.get(stage, "")
    gender_instruction = ""
    if user_gender and language == "he":
        gender_instruction = f"\n- התאם את הלשון למגדר: {user_gender} (זכר=תהיה/תחשוב, נקבה=תהיי/תחשבי)"
    
    missing_info = ""
    if missing:
        missing_info = f"\n**מה חסר ספציפית:** {missing}"
    
    prompt = f"""אתה מאמן אמפתי בתהליך BSD. המשתמש ענה תשובה שלא מספיקה, ואתה צריך לעזור לו.

**השלב הנוכחי:** {stage.value} - {stage_requirement}
**תשובת המשתמש:** "{user_message}"
**הבעיה שזוהתה:** {generic_critique_label or "לא ספציפי מספיק"}
**סוג התיקון הנדרש:** {repair_intent}{missing_info}

---

**תפקידך:**
לייצר שאלה/הנחיה **קצרה ואמפתית** שתעזור למשתמש לתת תשובה טובה יותר.

**עקרונות:**
- קצר (1-2 משפטים מקסימום)
- ספציפי לשלב הנוכחי
- אמפתי ומעודד (לא שיפוטי!)
- כולל דוגמה אם רלוונטי
- בשפה: {language}{gender_instruction}

**דוגמאות לפי repair_intent:**

**ASK_EXAMPLE:**
"תן/י דוגמה קונקרטית: **מה קרה** ו**עם מי**? (לדוגמה: 'אתמול ביקשתי מהילד לעשות שיעורים והוא סירב')"

**ENCOURAGE_TRY:**
"אני מבין/ה שזה לא פשוט. בואו ננסה ביחד - מה דבר אחד שאתה זוכר מהסיטואציה הזו?"

**ASK_ONE_SENTENCE:**
"איזה משפט אחד עבר לך בראש באותו רגע? (לדוגמה: 'אני אב רע', 'הוא לא מכבד אותי')"

**ASK_MORE_EMOTIONS:**
"איזה עוד רגש היה שם? (לדוגמה: עצב, פחד, בושה)"

**ASK_SPECIFIC_ACTION:**
"מה **עשית** בפועל? (פעולה קונקרטית, לדוגמה: 'צעקתי עליו')"

**ASK_THOUGHT_NOT_ACTION:**
"אני מחפש **מחשבה** - משפט שחשבת בראש (לא מה שעשית)"

**ASK_EMOTION_NOT_THOUGHT:**
"אני מחפש **רגש** - תחושה פנימית (כעס, עצב, פחד), לא מחשבה"

**REFOCUS:**
"בואו נחזור לשלב הנוכחי - {stage_requirement}"

---

**החזר רק את ההנחיה (בלי JSON, בלי הסברים):**
"""
    
    try:
        response = await llm.ainvoke(prompt)
        guidance = response.content.strip()
        logger.info(f"[DYNAMIC GUIDANCE] Generated for {repair_intent}: {guidance[:50]}...")
        return guidance
    except Exception as e:
        logger.error(f"[DYNAMIC GUIDANCE] Failed: {e}")
        # Fallback to generic prompt
        from .scripts import get_loop_prompt
        try:
            return get_loop_prompt(stage, language=language, gender=user_gender)
        except Exception:
            return "בואו ננסה שוב?" if language == "he" else "Let's try again?"


def _audit_verbatim_script(output_text: str, script: str) -> bool:
    """
    Hard guardrail: Verifies that the required script appears verbatim as a suffix.
    """
    out = (output_text or "").rstrip()
    scr = (script or "").rstrip()
    return out.endswith(scr)


def _detect_invalid_input(user_message: str, language: str) -> tuple[bool, str | None]:
    """
    Detects invalid input patterns (numbers, gibberish).
    
    Returns:
        (is_invalid, helpful_message)
    """
    msg = (user_message or "").strip()
    
    # Check for number-only input (e.g., "1,2,3,4" or "1 2 3 4")
    if re.match(r'^[\d\s,./]+$', msg):
        if language == "he":
            return True, "אני רואה מספרים. בשלב הזה אנחנו כותבים שמות של רגשות. לדוגמה: פחד, בושה, עלבון..."
        else:
            return True, "I see numbers. At this stage, we write names of emotions. For example: fear, shame, hurt..."
    
    # Check for extremely short input that's not meaningful
    if len(msg) < 2:
        return True, None  # Will use generic loop prompt
    
    return False, None


async def generate_coach_message(
    *,
    stage: str | StageId,
    language: str,
    user_message: str,
    critique: str,
    intent: str = "ANSWER_OK",  # New: from router
    is_loop: bool = False,
    missing_count: int = 1,
    missing: dict = None,  # New: what's missing
    user_name: str | None = None,
    user_gender: str | None = None,
    recent_openers: list[str] = None,  # New: for anti-repetition
    cognitive_data: dict = None,  # New: for richer context
    state = None,  # NEW: BsdState for insight analysis
    repair_intent: str | None = None,  # New: from Generic Critique (e.g. "ASK_EXAMPLE", "ENCOURAGE_TRY")
    generic_critique_label: str | None = None,  # New: from Generic Critique (e.g. "TOO_VAGUE", "AVOIDANCE")
    generic_critique_confidence: float | None = None,  # New: confidence score 0.0-1.0
    loop_count: int = 0,  # NEW: for stuck-loop detection in conversational_coach
) -> tuple[str, str | None]:
    """
    Generates the visible coach message (Talker's output).
    
    ENTERPRISE BEHAVIOR:
    - ADVANCE mode: reflection + FULL SCRIPT (verbatim)
    - LOOP mode: acknowledgment + SHORT LOOP PROMPT (NOT full script!)
    - INVALID INPUT: helpful correction message
    - DYNAMIC OPENERS: Uses LLM to generate natural, non-robotic openers (anti-repetition)
    - CONTEXTUAL: Aware of cognitive_data (topic, emotions) for richer responses
    
    This avoids the "broken record" feeling and maintains user trust.
    
    Args:
        stage: Current stage ID (e.g., "S0", "S1").
        language: "he" or "en".
        user_message: What the user said.
        critique: Hidden instructions from Reasoner (contains context about loop).
        is_loop: If True, we're looping in the same stage.
        missing_count: For S3 loops, how many emotions are still missing.
        recent_openers: List of recent openers (for anti-repetition check).
        cognitive_data: Accumulated session data for richer, contextual responses.
    
    Returns:
        (coach_message, opener_used) - The complete coach message and the opener that was used (or None).
    """
    stg = StageId(stage) if not isinstance(stage, StageId) else stage
    recent_openers = recent_openers or []
    cognitive_data = cognitive_data or {}
    
    # FEATURE FLAG: Use conversational coach instead of rigid scripts
    # Default to TRUE - we want natural conversation!
    use_conversational = os.getenv("BSD_CONVERSATIONAL_MODE", "true").lower() == "true"
    
    # If conversational mode is enabled, use natural conversation
    # (works for ALL intents except special cases that need specific feedback)
    
    # S5 EXCEPTION: REMOVED! 
    # Old logic: Don't use conversational on first turn (asking for actual action)
    # New logic: ALWAYS use conversational_coach for S5!
    # Reason: conversational_coach knows to summarize thought + vulnerable detection
    # before asking "what did you do?". This is CRITICAL for natural flow.
    is_s5_first_turn = False  # Always False - let conversational_coach handle S5
    
    # Check if S1 or S2_READY (never use conversational - always use hardcoded script!)
    is_s1 = (stg == StageId.S1)
    is_s2_ready = (stg == StageId.S2_READY)
    
    should_use_conversational = (
        use_conversational and 
        # Note: S1 NOW uses conversational_coach (with stage context injection!)
        not is_s2_ready and  # NEVER use conversational for S2_READY (must show full 3-question script!)
        not is_s5_first_turn and  # Don't use conversational on S5 first turn
        # 🔧 REMOVED S3_NOT_EMOTION and S3_UNCLEAR_EMOTION - let conversational_coach handle with stuck-loop detection!
        intent not in ["STOP", "ADVICE_REQUEST", "METHODOLOGY_CLARIFY"]
        # ⚠️ CRITICAL: Let conversational_coach handle ALL S1 cases (including S1_CONFIRM)!
        # This allows Insight Analyzer to detect external attribution, cumulative patterns, etc.
        # Script mode in talker.py is ONLY for special intents (STOP, ADVICE_REQUEST, METHODOLOGY_CLARIFY)
    )
    
    if should_use_conversational:
        try:
            natural_response = await generate_natural_response(
                stage=stg.value,
                language=language,
                user_message=user_message,
                intent=intent,
                decision="advance" if intent == "ANSWER_OK" else "loop",
                next_stage=stg.value if intent == "ANSWER_PARTIAL" else None,
                cognitive_data=cognitive_data,
                missing=missing or {},
                state=state,  # ✨ CRITICAL: Pass state for insight analysis!
                user_name=user_name,
                user_gender=user_gender,
                loop_count=loop_count,  # ✨ NEW: Pass loop count for stuck-loop detection!
            )
            logger.info(f"🗣️ [CONVERSATIONAL MODE] Generated natural response")
            return (natural_response, None)  # No separate opener in conversational mode
        except Exception as e:
            logger.error(f"[CONVERSATIONAL ERROR] Falling back to script mode: {e}")
            # Fall through to script mode
    
    # ==========================================
    # DETERMINISTIC RESPONSES (no LLM needed)
    # ==========================================
    # These return (message, None) - no opener to track
    
    # METHODOLOGY QUESTIONS (RAG) - All stages
    if intent == "METHODOLOGY_CLARIFY" or critique == "METHODOLOGY_CLARIFY":
        logger.info(f"🔍 [TALKER {stg.value}] Answering methodology question with RAG")
        
        # Get RAG service
        rag_service = get_rag_service()
        
        if rag_service.is_available:
            try:
                # Get answer from RAG
                rag_answer = await rag_service.answer_question(
                    question=user_message,
                    language=language
                )
                
                if rag_answer:
                    logger.info(f"✅ [TALKER {stg.value}] RAG answer found, returning to track")
                    
                    # BUILD FULL RESPONSE: RAG answer + return to current stage
                    
                    if stg == StageId.S0:
                        # At S0, return to consent question
                        if language == "he":
                            full_response = f"{rag_answer}\n\nהאם יש לי רשות להתחיל?"
                        else:
                            full_response = f"{rag_answer}\n\nDo I have your permission to begin?"
                    
                    else:
                        # At other stages, return to current stage question
                        try:
                            current_question = get_loop_prompt(
                                stg, 
                                language=language, 
                                missing=missing_count,
                                gender=user_gender
                            )
                            
                            if language == "he":
                                full_response = f"{rag_answer}\n\nאז, {current_question}"
                            else:
                                full_response = f"{rag_answer}\n\nSo, {current_question}"
                        
                        except ScriptNotFoundError:
                            # Fallback if no loop prompt
                            if language == "he":
                                full_response = f"{rag_answer}\n\nנמשיך?"
                            else:
                                full_response = f"{rag_answer}\n\nShall we continue?"
                    
                    return (full_response, None)
                
            except Exception as e:
                logger.error(f"❌ [TALKER {stg.value}] RAG failed: {e}")
        
        # Fallback if RAG not available or failed
        logger.info(f"⚠️  [TALKER {stg.value}] No RAG answer, using generic + returning to track")
        
        if stg == StageId.S0:
            if language == "he":
                return ((
                    "שאלה טובה! תהליך BSD (ביטחון-שיבה-דביקות) הוא שיטת אימון מובנית.\n"
                    "נוכל להתעמק בזה יותר תוך כדי התהליך.\n\n"
                    "האם יש לי רשות להתחיל?"
                ), None)
            else:
                return ((
                    "Great question! BSD is a structured coaching methodology.\n"
                    "We can explore this more during the process.\n\n"
                    "Do I have permission to begin?"
                ), None)
        else:
            # Return to current stage question
            try:
                current_question = get_loop_prompt(stg, language=language, gender=user_gender)
                if language == "he":
                    return ((
                        "שאלה מעניינת! נוכל להתעמק בזה יותר.\n\n"
                        f"אז, {current_question}"
                    ), None)
                else:
                    return ((
                        "Interesting question! We can explore this more.\n\n"
                        f"So, {current_question}"
                    ), None)
            except ScriptNotFoundError:
                # Fallback
                if language == "he":
                    return ("שאלה מעניינת! נמשיך?", None)
                else:
                    return ("Interesting question! Shall we continue?", None)
    
    # S0 special responses
    if stg == StageId.S0 and critique == "S0_CLARIFY":
        logger.info(f"🗣️ [TALKER S0] Providing clarification response")
        if language == "he":
            return ((
                "כוונתי: להתחיל תהליך אימון מובנה שבו אני שואל שאלות ולא נותן עצות.\n"
                "האם יש לי רשות להתחיל?"
            ), None)
        else:
            return ((
                "I mean: to begin a structured coaching process where I ask questions and don't give advice.\n"
                "Do I have your permission to begin?"
            ), None)
    
    # STOP intent (S0 only)
    if intent == "STOP" or critique == "STOP":
        logger.info(f"🗣️ [TALKER S0] STOP - User refused")
        if language == "he":
            text = "בסדר גמור. אם תרצה/י לחזור לזה בהמשך — אני כאן."
            return (adapt_to_gender(text, user_gender, language), None)
        else:
            return ("Understood. If you want to come back to this later — I'm here.", None)
    
    # READINESS CHECK - Low self-belief (S2_READY)
    if critique == "READINESS_LOW_SELF_BELIEF":
        logger.info(f"🗣️ [TALKER S2_READY] LOW_SELF_BELIEF - stopping process")
        if language == "he":
            text = (
                "אני שומע/ת אותך.\n\n"
                "אימון דורש **כוחות קיימים** ('יש') – מקום שממנו אפשר לפעול.\n"
                "כשאנחנו מרגישים 'אין לי כוח' או 'לא מסוגל/ת', זה אולי לא הזמן לאימון.\n\n"
                "אולי כדאי לחשוב על **ריפוי** או **טיפול תומך** קודם – מקום שיחזיר את הכוחות.\n\n"
                "אני כאן אם תרצה/י לחזור כשזה ירגיש נכון."
            )
            return (adapt_to_gender(text, user_gender, language), None)
        else:
            return ((
                "I hear you.\n\n"
                "Coaching requires **existing capacity** ('Yesh') – a place from which you can act.\n"
                "When we feel 'I have no strength' or 'I'm not capable', it may not be the time for coaching.\n\n"
                "Perhaps consider **healing** or **supportive therapy** first – a place that will restore your capacity.\n\n"
                "I'm here if you want to come back when it feels right."
            ), None)
    
    # ADVICE_REQUEST intent (all stages)
    if intent == "ADVICE_REQUEST" or critique == "ADVICE_BLOCK":
        logger.info(f"🗣️ [TALKER {stg.value}] ADVICE_REQUEST - blocking")
        if language == "he":
            return ((
                "בשלב הזה אני לא נותן עצות או פתרונות.\n"
                "האם יש רשות להמשיך בשלב הנוכחי?"
            ), None)
        else:
            return ((
                "At this stage, I don't provide advice or solutions.\n"
                "Do I have permission to continue with the current stage?"
            ), None)
    
    # META-DISCUSSION - user asking about the process itself
    if intent == "META_DISCUSSION" or critique == "META_DISCUSSION":
        logger.info(f"🗣️ [TALKER {stg.value}] META_DISCUSSION")
        stage_names_he = {
            "S0": "רשות (permission)",
            "S1": "נושא (topic)",
            "S2": "אירוע (specific event)",
            "S2_READY": "בדיקת נכונות (readiness check)",
            "S3": "רגשות (emotions)",
            "S4": "מחשבה (thought)",
            "S5": "מעשה (action)",
            "S6": "פער (gap)",
            "S7": "דפוס (pattern)",
            "S8": "עמדה/רצון (stance/desire)",
            "S9": "כמ\"ז (source forces)",
            "S10": "בחירה ומחויבות (commitment)",
        }
        stage_names_en = {
            "S0": "Permission",
            "S1": "Topic",
            "S2": "Specific Event",
            "S2_READY": "Readiness Check",
            "S3": "Emotions",
            "S4": "Thought",
            "S5": "Action",
            "S6": "Gap",
            "S7": "Pattern",
            "S8": "Stance/Desire",
            "S9": "Source Forces",
            "S10": "Commitment",
        }
        stage_name = (stage_names_he if language == "he" else stage_names_en).get(stg.value, stg.value)
        
        if language == "he":
            text = (
                f"אנחנו כרגע בשלב **{stage_name}**.\n"
                "הוא חלק מהמסע שעוברים יחד — כל שלב מעמיק את ההבנה.\n"
                "בואו נמשיך?"
            )
            return (adapt_to_gender(text, user_gender, language), None)
        else:
            return ((
                f"We're currently in the **{stage_name}** stage.\n"
                "It's part of our journey together — each stage deepens understanding.\n"
                "Shall we continue?"
            ), None)
    
    # OFFTRACK intent (all stages)
    if intent == "OFFTRACK" or critique == "OFFTRACK":
        logger.info(f"🗣️ [TALKER {stg.value}] OFFTRACK")
        if language == "he":
            return ((
                "נראה שזו תשובה שלא מתאימה לשלב הזה.\n"
                "בואו ננסה שוב."
            ), None)
        else:
            return ((
                "This doesn't seem to fit the current stage.\n"
                "Let's try again."
            ), None)
    
    # S3 SPECIAL: NOT_EMOTION (e.g., numbers, actions)
    if intent == "S3_NOT_EMOTION":
        logger.info(f"🗣️ [TALKER S3] NOT_EMOTION - invalid tokens")
        invalid_tokens = missing.get("invalid_tokens", []) if missing else []
        
        # Don't list individual words - just give a gentle reminder
        if language == "he":
            text = (
                "אני מחפש רגשות — תחושות פנימיות.\n"
                "לדוגמה: כעס, בושה, פחד, עצב, שמחה, תסכול.\n\n"
                "איזה רגש היה לך באותו רגע?"
            )
            return (adapt_to_gender(text, user_gender, language), None)
        else:
            return ((
                "I'm looking for emotions — internal feelings.\n"
                "For example: anger, shame, fear, sadness, joy, frustration.\n\n"
                "What emotion did you feel in that moment?"
            ), None)
    
    # S3 SPECIAL: UNCLEAR_EMOTION (e.g., typo, slang)
    if intent == "S3_UNCLEAR_EMOTION":
        logger.info(f"🗣️ [TALKER S3] EMOTION_UNCLEAR - clarification needed")
        unclear_tokens = missing.get("clarify_emotions", []) if missing else []
        tokens_str = ", ".join(f"'{t}'" for t in unclear_tokens) if unclear_tokens else "מה ששלחת"
        
        if language == "he":
            return ((
                f"שמעתי: {tokens_str}\n"
                "רק לוודא — האם זה שם של רגש?\n"
                "אם כן, תוכל/י לכתוב אותו שוב בצורה ברורה יותר?"
            ), None)
        else:
            return ((
                f"I heard: {tokens_str}\n"
                "Just to confirm — is that the name of an emotion?\n"
                "If so, could you write it again more clearly?"
            ), None)
    
    # CLARIFY intent - user is asking a question (generic, NOT specific to correction)
    # BUT: S1 specialized critiques take priority!
    if intent == "CLARIFY":
        # Exception: If there's a specific S1 critique, let S1 responses handle it
        s1_specific_critiques = ["S1_GOAL_NOT_TOPIC", "S1_TOO_BROAD", "S1_CONFIRM", "S1_OFFTRACK", "S1_CLARIFY"]
        if stg == StageId.S1 and critique in s1_specific_critiques:
            logger.info(f"🗣️ [TALKER S1] CLARIFY + {critique} - letting S1 specialized response handle")
            # Fall through to S1 specialized responses below
        else:
            logger.info(f"🗣️ [TALKER {stg.value}] CLARIFY - user asking a question")
            
            # Check if it's a correction
            if any(word in user_message.lower() for word in ["mistake", "טעות", "correction", "meant to say", "התכוונתי"]):
                logger.info(f"🗣️ [TALKER {stg.value}] User is correcting themselves")
                if language == "he":
                    text = (
                        "אני מצטער, הבנתי לא נכון.\n"
                        "מה התכוונת להגיד?"
                    )
                    return (adapt_to_gender(text, user_gender, language), None)
                else:
                    return ((
                        "I apologize, I misunderstood.\n"
                        "What did you mean to say?"
                    ), None)
            
            # Generic clarification question (not methodology)
            try:
                current_question = get_loop_prompt(stg, language=language, gender=user_gender)
                if language == "he":
                    return ((
                        "שאלה טובה! אשמח לענות עליה.\n\n"
                        f"בינתיים, {current_question}"
                    ), None)
                else:
                    return ((
                        "Good question! I'd be happy to answer.\n\n"
                        f"Meanwhile, {current_question}"
                    ), None)
            except ScriptNotFoundError:
                # Fallback
                if language == "he":
                    return ("שאלה טובה! נמשיך?", None)
                else:
                    return ("Good question! Shall we continue?", None)
    
    # S1 specialized responses (from S1 Router)
    if stg == StageId.S1:
        if critique == "S1_CONFIRM":
            logger.info(f"🗣️ [TALKER S1] S1_CONFIRM - unclear topic")
            if language == "he":
                text = (
                    "שמעתי אותך.\n"
                    "רק כדי לדייק — על מה היית רוצה להתאמן? ספר/י את הנושא במילה או שתיים.\n"
                    "(לדוגמה: הורות, זוגיות, עבודה)"
                )
                return (adapt_to_gender(text, user_gender, language), None)
            else:
                return ((
                    "I hear you.\n"
                    "Just to clarify — what would you like to coach on? Write the topic in a word or two.\n"
                    "(For example: parenting, relationships, work)"
                ), None)
        
        elif critique == "S1_OFFTRACK":
            logger.info(f"🗣️ [TALKER S1] S1_OFFTRACK")
            if language == "he":
                text = (
                    "כדי להתחיל אימון אני צריך נושא קצר.\n"
                    "על מה היית רוצה להתאמן היום? (מילה או משפט)"
                )
                return (adapt_to_gender(text, user_gender, language), None)
            else:
                return ((
                    "To start coaching, I need a brief topic.\n"
                    "What would you like to coach on today? (A word or sentence)"
                ), None)
        
        elif critique == "S1_CLARIFY":
            logger.info(f"🗣️ [TALKER S1] S1_CLARIFY - user asking for clarification")
            
            # Check for specific clarification questions
            user_lower = user_message.lower()
            is_asking_if_too_broad = any(word in user_lower for word in ["רחב מדי", "too broad", "רחב", "כן רחב"])
            is_asking_what_means = any(word in user_lower for word in ["מה הכוונה", "מה זאת אומרת", "what do you mean", "what does that mean"])
            
            if is_asking_if_too_broad and language == "he":
                # User is asking if their answer is too broad
                text = (
                    "זה תלוי בספציפיות! 🎯\n\n"
                    "אם זה **תחום כללי אחד** (כמו 'הורות', 'עבודה') - זה רחב מדי.\n"
                    "אם זה **אתגר ספציפי** (כמו 'השגת יעדים גדולים', 'כעסים על הילדים') - זה מצוין!\n\n"
                    "אז, מה הנושא שאתה רוצה להתאמן עליו?"
                )
                return (adapt_to_gender(text, user_gender, language), None)
            elif is_asking_what_means and language == "he":
                # User is asking what we mean by "topic"
                text = (
                    "אני מחפש את **הנושא/אתגר** שאיתו תרצה/י לעבוד.\n\n"
                    "**דוגמאות טובות:**\n"
                    "✓ 'השגת יעדים גדולים'\n"
                    "✓ 'כעסים על הילדים'\n"
                    "✓ 'הקשבה לבן המתבגר'\n"
                    "✓ 'בושה מול אנשים'\n\n"
                    "**לא נושא:**\n"
                    "❌ 'להיות אבא טוב' (זו מטרה)\n"
                    "❌ 'הורות' (רחב מדי)\n\n"
                    "אז, על מה תרצה/י להתאמן?"
                )
                return (adapt_to_gender(text, user_gender, language), None)
            else:
                # Generic clarification
                if language == "he":
                    text = (
                        "כוונתי לנושא של האימון — התחום שבו תרצה/י לעשות שינוי.\n"
                        "על מה היית רוצה להתאמן היום? (מילה או משפט)"
                    )
                    return (adapt_to_gender(text, user_gender, language), None)
                else:
                    return ((
                        "I mean the topic of the coaching — the area where you'd like to make a change.\n"
                        "What would you like to coach on today? (A word or sentence)"
                    ), None)
        
        elif critique == "S1_GOAL_NOT_TOPIC":
            logger.info(f"🗣️ [TALKER S1] S1_GOAL_NOT_TOPIC - user gave goal, not topic")
            if language == "he":
                text = (
                    "זו מטרה חשובה ומשמעותית! 💚\n"
                    "\n"
                    "כדי שנוכל לעבוד על זה ביעילות, אני צריך **תחום ספציפי**:\n"
                    "**על איזה נושא** תרצה/י להתאמן כדי להגיע לשם?\n"
                    "\n"
                    "(לדוגמה: הקשבה לילדים, ניהול כעסים, קביעת גבולות...)"
                )
                return (adapt_to_gender(text, user_gender, language), None)
            else:
                return ((
                    "That's an important and meaningful goal! 💚\n"
                    "\n"
                    "To work on this effectively, I need a **specific area**:\n"
                    "**What topic** would you like to coach on to get there?\n"
                    "\n"
                    "(For example: listening to kids, anger management, setting boundaries...)"
                ), None)
        
        elif critique == "S1_TOO_BROAD":
            logger.info(f"🗣️ [TALKER S1] S1_TOO_BROAD - topic too general")
            if language == "he":
                text = (
                    "זה תחום רחב! 🎯\n"
                    "\n"
                    "**מה בתוך זה** הכי מעניין אותך להתאמן עליו עכשיו?\n"
                    "(ככל שתהיה/י ספציפי/ת יותר, כך נוכל לעבוד לעומק)"
                )
                return (adapt_to_gender(text, user_gender, language), None)
            else:
                return ((
                    "That's a broad area! 🎯\n"
                    "\n"
                    "**What within it** interests you most to coach on right now?\n"
                    "(The more specific you are, the deeper we can work)"
                ), None)
    
    # S2 specialized responses - event not specific enough
    if stg == StageId.S2 and critique == "S2_NOT_SPECIFIC":
        logger.info(f"🗣️ [TALKER S2] S2_NOT_SPECIFIC - event needs more details")
        if language == "he":
            text = (
                "כדי לעבוד בדיוק, צריך רגע ספציפי מהחיים.\n\n"
                "תאר/י אירוע אחד שקרה לאחרונה:\n"
                "• **מתי** זה קרה?\n"
                "• **עם מי** היית?\n"
                "• **מה** בדיוק קרה?\n\n"
                "דוגמה: \"אתמול בערב אמרתי לבן שלי לעשות שיעורים, הוא סירב, ואני צעקתי.\""
            )
            return (adapt_to_gender(text, user_gender, language), None)
        else:
            return ((
                "To work precisely, I need a specific moment from your life.\n\n"
                "Describe one event that happened recently:\n"
                "• **When** did it happen?\n"
                "• **Who** were you with?\n"
                "• **What** exactly happened?\n\n"
                "Example: \"Yesterday evening I asked my son to do homework, he refused, and I shouted.\""
            ), None)
    
    # S4 specialized responses - thought incomplete
    if stg == StageId.S4 and critique == "S4_INCOMPLETE":
        logger.info(f"🗣️ [TALKER S4] S4_INCOMPLETE - thought seems cut off")
        if language == "he":
            text = (
                "נראה שהמחשבה לא הושלמה.\n\n"
                "אפשר להשלים?\n"
                "(מחפש משפט שלם שעובר לך בראש באותו רגע)"
            )
            return (adapt_to_gender(text, user_gender, language), None)
        else:
            return ((
                "It seems the thought wasn't completed.\n\n"
                "Can you finish it?\n"
                "(Looking for a complete sentence going through your head at that moment)"
            ), None)
    
    # S5 SPECIAL: Two-turn stage (actual → desired)
    if stg == StageId.S5 and intent == "ANSWER_PARTIAL":
        missing = missing or {}
        if "action_desired" in missing:
            # User gave actual, now ask for desired
            logger.info(f"🗣️ [TALKER S5] Got actual, now asking for desired")
            if language == "he":
                text = (
                    "שמעתי את מה שעשית בפועל.\n"
                    "\n"
                    "ועכשיו, נסתכל על המצב האידיאלי:\n"
                    "איך היית רוצה להרגיש באותו רגע?\n"
                    "מה היית רוצה לחשוב?\n"
                    "איך היית רוצה לפעול?"
                )
                return (adapt_to_gender(text, user_gender, language), None)
            else:
                return ((
                    "I hear what you actually did.\n"
                    "\n"
                    "And now, let's look at the ideal state:\n"
                    "How would you want to feel in that moment?\n"
                    "What would you want to think?\n"
                    "How would you want to act?"
                ), None)
        elif "action_actual" in missing:
            # User jumped to desired, ask for actual first
            logger.info(f"🗣️ [TALKER S5] User jumped to desired, asking for actual")
            if language == "he":
                return ((
                    "רגע, בואו נתחיל מהעובדות.\n"
                    "מה עשית **בפועל** באותה סיטואציה?"
                ), None)
            else:
                return ((
                    "Hold on, let's start with the facts.\n"
                    "What did you **actually** do in that situation?"
                ), None)
    
    # ANSWER_PARTIAL with confirmation request (truncated input - other stages)
    missing = missing or {}
    if intent == "ANSWER_PARTIAL" and any(k.startswith("confirm_") for k in missing.keys()):
        logger.info(f"🗣️ [TALKER {stg.value}] ANSWER_PARTIAL (confirm)")
        
        # Stage-specific confirmation messages (non-S1)
        if stg == StageId.S1 and "confirm_topic" in missing:
            # Already handled above, but keep as fallback
            if language == "he":
                return ((
                    "שמעתי.\n"
                    "רק לוודא — למה התכוונת?\n"
                    "(לדוגמה: הורות, זוגיות, עבודה…)"
                ), None)
            else:
                return ((
                    "I hear you.\n"
                    "Just to confirm — what did you mean?\n"
                    "(For example: parenting, relationships, work…)"
                ), None)
        
        elif stg == StageId.S6 and "confirm_gap_name" in missing:
            if language == "he":
                return ((
                    "שמעתי.\n"
                    "רק לוודא — איך היית רוצה לקרוא לפער הזה?\n"
                    "תוכל/י לנסח אותו במילה או שתיים?"
                ), None)
            else:
                return ((
                    "I hear you.\n"
                    "Just to confirm — how would you like to name this gap?\n"
                    "Can you phrase it in a word or two?"
                ), None)
        
        # Generic confirmation (fallback)
        if language == "he":
            return ((
                "שמעתי.\n"
                "רק לוודא — תוכל/י לנסח את זה במילה או שתיים?"
            ), None)
        else:
            return ((
                "I hear you.\n"
                "Just to confirm — can you phrase it in a word or two?"
            ), None)
    
    # ==========================================
    # FALLBACK RESPONSES (edge cases)
    # ==========================================
    
    if stg == StageId.S0 and critique == "S0_REDIRECT_TO_CONSENT":
        logger.info(f"🗣️ [TALKER S0] Redirecting to consent")
        if language == "he":
            return ((
                "שמעתי אותך.\n"
                "כדי להתחיל אני צריך רשות מפורשת להיכנס לתהליך.\n"
                "האם יש לי רשות להתחיל?"
            ), None)
        else:
            return ((
                "I hear you.\n"
                "To begin, I need explicit permission to enter the process.\n"
                "Do I have your permission to start?"
            ), None)
    
    # Check for invalid input (numbers, gibberish)
    is_invalid, correction_msg = _detect_invalid_input(user_message, language)
    if is_invalid and correction_msg:
        logger.info(f"🚨 [TALKER {stg.value}] Invalid input detected, providing correction")
        return (correction_msg, None)
    
    # ==========================================
    # DYNAMIC OPENER GENERATION (anti-robotics)
    # ==========================================
    is_advance = (intent == "ANSWER_OK")
    opener_result = await generate_opener(
        user_message=user_message,
        language=language,
        stage=stg.value,
        is_advance=is_advance,
        critique=critique,
        recent_openers=recent_openers,
        cognitive_data=cognitive_data,  # Pass context for richer openers!
        user_gender=user_gender  # Pass gender for automatic adaptation!
    )
    
    # ==========================================
    # DYNAMIC GUIDANCE (if Generic Critique detected issue)
    # ==========================================
    
    # If Generic Critique provided a repair_intent with high confidence, use Dynamic Guidance
    # This overrides the standard loop prompt for a more natural, context-aware response
    if (
        repair_intent and 
        repair_intent != "none" and 
        generic_critique_confidence and 
        generic_critique_confidence > 0.6  # Only use if confident
    ):
        try:
            logger.info(
                f"🧠 [DYNAMIC GUIDANCE] Using repair_intent={repair_intent} "
                f"(confidence={generic_critique_confidence:.2f})"
            )
            dynamic_guidance = await generate_dynamic_guidance(
                stage=stg,
                language=language,
                user_message=user_message,
                repair_intent=repair_intent,
                generic_critique_label=generic_critique_label,
                missing=missing,
                user_gender=user_gender
            )
            
            # Return dynamic guidance directly (no opener needed - it's already natural)
            logger.info(f"✅ [DYNAMIC GUIDANCE] Generated: {dynamic_guidance[:50]}...")
            return (dynamic_guidance, None)
        
        except Exception as e:
            logger.error(f"❌ [DYNAMIC GUIDANCE] Failed: {e}, falling back to loop prompt")
            # Fall through to standard loop prompt
    
    # ==========================================
    # VULNERABLE MOMENT HANDLING 
    # ==========================================
    # Now handled entirely by conversational_coach.py!
    # conversational_coach has sophisticated detection + few-shot examples
    # that handle vulnerable moments properly with pause + summary.
    vulnerable_acknowledgment = None
    
    # ==========================================
    # COMPOSE FINAL MESSAGE (opener + script)
    # ==========================================
    
    # Choose script type: LOOP PROMPT (short) or FULL SCRIPT (advance)
    if is_loop:
        try:
            script = get_loop_prompt(stg, language=language, missing=missing_count, gender=user_gender)
            logger.debug(f"🗣️ [TALKER {stg.value}] Using LOOP PROMPT (short, focused, gender={user_gender})")
        except ScriptNotFoundError:
            # Fallback to full script if loop prompt missing
            script = get_script(stg, language=language, gender=user_gender)
            logger.warning(f"🗣️ [TALKER {stg.value}] Loop prompt not found, using full script")
    else:
        script = get_script(stg, language=language, gender=user_gender)
        logger.debug(f"🗣️ [TALKER {stg.value}] Using FULL SCRIPT (advance, gender={user_gender})")
    
    # Compose final message: vulnerable acknowledgment + opener (if any) + script
    try:
        parts = []
        
        # Add vulnerable acknowledgment if present
        if vulnerable_acknowledgment:
            parts.append(vulnerable_acknowledgment)
            logger.info(f"💔 [VULNERABLE] Added acknowledgment: '{vulnerable_acknowledgment}'")
        
        # Add opener if present
        if opener_result.use_opener and opener_result.opener:
            parts.append(opener_result.opener)
            logger.info(f"✅ [TALKER {stg.value}] Using dynamic opener: '{opener_result.opener[:40]}...'")
        
        # Add script
        parts.append(script)
        
        # Join with proper spacing
        final_message = "\n\n".join(parts)
        
        # Return with opener (if any) for tracking
        return_opener = vulnerable_acknowledgment or (opener_result.opener if opener_result.use_opener else None)
        
        if vulnerable_acknowledgment:
            logger.info(f"✅ [TALKER {stg.value}] Vulnerable moment handled with acknowledgment")
        elif opener_result.use_opener:
            logger.info(f"✅ [TALKER {stg.value}] Using dynamic opener")
        else:
            logger.info(f"✅ [TALKER {stg.value}] No opener (direct to script)")
        
        return (final_message, return_opener)
    
    except Exception as e:
        logger.error(f"🗣️ [TALKER ERROR] {stg.value}: {e}")
        # Fail-safe on exception
        reflection = "שמעתי אותך." if language == "he" else "I hear you."
        return (f"{reflection}\n\n{script}", None)
