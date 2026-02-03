"""
Intent Router - Enterprise two-layer routing system.

Layer 1: Deterministic rules (fast, no LLM)
Layer 2: LLM classifier (only when needed)

Intents:
- ANSWER_OK: User met gate requirements
- ANSWER_PARTIAL: Partial answer (missing X)
- CLARIFY: User asks for clarification
- OFFTRACK: Irrelevant/invalid input
- ADVICE_REQUEST: User asks for advice/solution
- STOP: User refuses (S0 only)
"""

from typing import Dict, Any
import logging
import json
import re

from .stage_defs import StageId, next_stage
from .state_schema import BsdState
from .stage_gates import check_gate
from .llm import get_azure_chat_llm
from .reasoner import ReasonerDecision, _simple_emotion_list
from .router_s1 import route_s1
from .emotion_classifier import classify_emotion_token
from .generic_critique import (
    GenericCritiqueDetector,
    CritiqueLabel,
    RepairIntent,
    get_stage_requirement
)
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

# Initialize Generic Critique Detector (singleton)
_generic_critique_detector = None

def get_generic_critique_detector() -> GenericCritiqueDetector:
    """Get or create Generic Critique Detector singleton"""
    global _generic_critique_detector
    if _generic_critique_detector is None:
        _generic_critique_detector = GenericCritiqueDetector()
    return _generic_critique_detector


def _detect_clarification(user_message: str, language: str) -> bool:
    """Deterministic: Is this a clarification question or correction?"""
    msg = user_message.strip().lower()
    
    # Question markers
    has_question_mark = "?" in msg or "？" in msg
    
    # Clarification tokens
    clarify_tokens = [
        "במה", "מה", "מה זה", "מה הכוונה", "איך זה עובד", "תסביר",
        "what", "what do you mean", "what is", "how does", "explain", "clarify"
    ]
    
    # Correction tokens - user is correcting themselves!
    correction_tokens = [
        "טעות", "התכוונתי", "רגע", "שניה", "חכה", "לא מה שאמרתי",
        "mistake", "meant to say", "i meant", "wait", "hold on", "not what i said",
        "correction", "actually", "no i mean"
    ]
    
    has_clarify_token = any(tok in msg for tok in clarify_tokens)
    has_correction_token = any(tok in msg for tok in correction_tokens)
    
    return has_question_mark or has_clarify_token or has_correction_token


def _is_methodology_question(user_message: str, language: str) -> bool:
    """
    Deterministic: Is this a question about BSD methodology itself?
    
    This distinguishes between:
    - Methodology questions (needs RAG): "What is the Shiva process?", "Who founded BSD?"
    - Process questions (generic response): "What do you want from me?", "Why this question?"
    
    Returns True if the question is about BSD/methodology and should use RAG.
    """
    msg = user_message.strip().lower()
    
    # Methodology question markers
    methodology_markers = [
        # About the system/method
        "מה זה", "מהו", "מהי", "על מה מבוסס", "מי יסד", "מי פיתח", "מי כתב",
        "איך עובד", "מה המטרה", "למה צריך", "מה התהליך", "מה השיטה",
        "what is", "who founded", "who created", "who wrote", "how does it work",
        "what's the purpose", "what's the goal", "what's the method",
        
        # Wanting to learn/hear about the process
        "לשמוע על התהליך", "לשמוע קצת על התהליך", "לשמוע על השיטה", "לשמוע על האימון",
        "להבין את התהליך", "להבין את השיטה", "לדעת על התהליך", "לדעת על השיטה",
        "לקבל הסבר על", "תסביר לי על", "ספר לי על התהליך", "ספר לי על השיטה",
        "to hear about the process", "to understand the process", "to know about",
        "explain the process", "tell me about the process", "tell me about the method",
        
        # Specific BSD terms (in Hebrew and English)
        "השיבה", "הפער", "המצוי", "הרצוי", "ביטחון", "דביקות",
        "bsd", "shiva", "11 שלבים", "11 stages", "אחד עשר שלבים",
        "המסכים", "מסך הרגש", "מסך המחשבה", "מסך המעשה",
        "screen", "emotion screen", "thought screen", "action screen",
        
        # About methodology/approach
        "שיטה", "מתודולוגיה", "גישה", "תהליך האימון",
        "methodology", "approach", "coaching process",
        
        # About this specific coaching
        "אימון יהודי", "jewish coaching", "jewish coach",
        "מה המאמן", "what is the coach", "what's this coaching"
    ]
    
    return any(marker in msg for marker in methodology_markers)


def _detect_advice_request(user_message: str, language: str) -> bool:
    """Deterministic: Is this asking for advice/solution?"""
    msg = user_message.strip().lower()
    
    advice_markers = [
        "מה לעשות", "מה כדאי", "איך לפתור", "תן עצה", "תגיד לי מה",
        "what should i", "what to do", "how to solve", "give me advice", "tell me what"
    ]
    
    return any(marker in msg for marker in advice_markers)


def _detect_offtrack_simple(user_message: str, language: str) -> bool:
    """Deterministic: Simple offtrack detection (jokes, hello, numbers, etc.)."""
    msg = user_message.strip().lower()
    
    # Very short (< 2 chars)
    if len(msg) < 2:
        return True
    
    # Only numbers (no letters)
    if msg.replace(" ", "").replace(",", "").replace(".", "").isdigit():
        return True
    
    # Greetings/jokes - but ONLY if that's ALL they said
    # "שלום" alone = OFFTRACK
    # "שלום, כן" = NOT OFFTRACK (has content!)
    offtrack_only_patterns = ["היי", "שלום", "hello", "hi", "hey", "haha", "lol", "😂", "🤣"]
    
    # Check if the ENTIRE message is just a greeting
    # Remove common punctuation first
    msg_clean = msg.replace(",", "").replace(".", "").replace("!", "").replace("?", "").strip()
    
    # If after removing punctuation, it's just a greeting - OFFTRACK
    if msg_clean in offtrack_only_patterns:
        return True
    
    # If message has substance (length > 10 chars), it's probably not just a greeting
    if len(msg) > 10:
        return False
    
    # For short messages, check if it's ONLY a greeting (no other words)
    words = msg.split()
    if len(words) == 1 and words[0] in offtrack_only_patterns:
        return True
    
    return False


def _detect_s0_stop(user_message: str, language: str) -> bool:
    """Deterministic: S0 refusal/stop."""
    msg = user_message.strip().lower()
    
    # IMPORTANT: Filter out "false positives" - phrases that contain "no"/"לא" but are actually YES or QUESTIONS!
    # "למה לא" = "why not" = YES in Hebrew
    # "לא יודע" = "don't know" = QUESTION, not refusal!
    # "כן, אבל לא" = "yes, but I don't..." = partial YES with question
    false_positives = [
        "למה לא", "why not",           # "why not" = YES
        "לא יודע", "don't know", "i don't know",  # "don't know" = QUESTION
        "לא מבין", "don't understand", "i don't understand",  # "don't understand" = QUESTION
        "כן, אבל", "yes, but", "כן אבל"  # "yes, but..." = partial YES
    ]
    if any(phrase in msg for phrase in false_positives):
        return False  # It's NOT a refusal!
    
    stop_tokens = ["לא", "no", "תודה לא", "לא תודה", "no thanks", "stop", "עצור"]
    return any(tok == msg or tok + " " in msg or " " + tok in msg for tok in stop_tokens)


async def route_intent(
    *,
    stage: str,
    language: str,
    user_message: str,
    state: BsdState
) -> ReasonerDecision:
    """
    Enterprise two-layer intent routing.
    
    Layer 1: Deterministic rules (fast, no LLM)
    Layer 2: LLM classifier (only if needed)
    
    Args:
        stage: Current stage ID
        language: "he" or "en"
        user_message: User's message
        state: Current BSD state (for gates/accumulation)
    
    Returns:
        ReasonerDecision with intent, decision, extracted, missing
    """
    stg = StageId(stage) if not isinstance(stage, StageId) else stage
    
    # ====================
    # LAYER 1: DETERMINISTIC
    # ====================
    
    # PRIORITY PRINCIPLE:
    # If user gives a VALID ANSWER to the stage → that's the intent (ANSWER_OK)
    # Even if the answer contains methodology keywords, it's still an answer!
    # Only check METHODOLOGY_CLARIFY if the answer is NOT valid.
    
    # 1.1: S1 SPECIALIZED ROUTER (4 outcomes)
    if stg == StageId.S1:
        logger.info(f"[ROUTER S1] Using specialized S1 router")
        s1_route = await route_s1(user_message=user_message, language=language)
        
        if s1_route.intent == "TOPIC_CLEAR":
            return ReasonerDecision(
                intent="ANSWER_OK",
                decision="advance",
                next_stage=next_stage(stg).value,
                reasons=[s1_route.rationale or "Topic accepted"],
                extracted={"topic": s1_route.topic_candidate or user_message.strip()},
                missing={},
                critique=""
            )
        elif s1_route.intent == "GOAL_NOT_TOPIC":
            return ReasonerDecision(
                intent="CLARIFY",
                decision="loop",
                next_stage=None,
                reasons=[s1_route.rationale or "User provided goal, not topic"],
                extracted={"goal_mentioned": user_message.strip()},
                missing={"specific_topic": True},
                critique="S1_GOAL_NOT_TOPIC"
            )
        elif s1_route.intent == "TOO_BROAD":
            return ReasonerDecision(
                intent="CLARIFY",
                decision="loop",
                next_stage=None,
                reasons=[s1_route.rationale or "Topic too broad, needs narrowing"],
                extracted={"broad_topic": s1_route.topic_candidate or user_message.strip()},
                missing={"specific_topic": True},
                critique="S1_TOO_BROAD"
            )
        elif s1_route.intent == "CLARIFY":
            return ReasonerDecision(
                intent="CLARIFY",
                decision="loop",
                next_stage=None,
                reasons=[s1_route.rationale or "Clarification requested"],
                extracted={},
                missing={},
                critique="S1_CLARIFY"
            )
        elif s1_route.intent == "OFFTRACK":
            return ReasonerDecision(
                intent="OFFTRACK",
                decision="loop",
                next_stage=None,
                reasons=[s1_route.rationale or "Offtrack"],
                extracted={},
                missing={"topic": True},
                critique="S1_OFFTRACK"
            )
        else:  # TOPIC_UNCLEAR
            return ReasonerDecision(
                intent="ANSWER_PARTIAL",
                decision="loop",
                next_stage=None,
                reasons=[s1_route.rationale or "Unclear topic"],
                extracted={"topic_candidate": s1_route.topic_candidate} if s1_route.topic_candidate else {},
                missing={"confirm_topic": True},
                critique="S1_CONFIRM"
            )
    
    # 1.1: S0 STOP detection
    if stg == StageId.S0 and _detect_s0_stop(user_message, language):
        logger.info(f"[ROUTER S0] STOP detected: '{user_message[:30]}...'")
        return ReasonerDecision(
            intent="STOP",
            decision="stop",
            next_stage=None,
            reasons=["User refused to start coaching process."],
            extracted={},
            missing={},
            critique="STOP"
        )
    
    # 1.2: S0 CLARIFY detection (with methodology check)
    if stg == StageId.S0 and _detect_clarification(user_message, language):
        # Check if it's a methodology question (needs RAG)
        if _is_methodology_question(user_message, language):
            logger.info(f"[ROUTER S0] METHODOLOGY_CLARIFY detected: '{user_message[:30]}...'")
            return ReasonerDecision(
                intent="METHODOLOGY_CLARIFY",
                decision="loop",
                next_stage=None,
                reasons=["User asked about BSD methodology."],
                extracted={"question": user_message},
                missing={},
                critique="METHODOLOGY_CLARIFY"
            )
        else:
            # Regular clarify (about current process)
            logger.info(f"[ROUTER S0] CLARIFY (process) detected: '{user_message[:30]}...'")
            return ReasonerDecision(
                intent="CLARIFY",
                decision="loop",
                next_stage=None,
                reasons=["User asked for clarification at S0."],
                extracted={},
                missing={},
                critique="S0_CLARIFY"
            )
    
    # 1.3: ADVICE_REQUEST detection (all stages)
    # This MUST come before Gate checking because giving advice is dangerous
    if _detect_advice_request(user_message, language):
        logger.info(f"[ROUTER {stg.value}] ADVICE_REQUEST detected")
        return ReasonerDecision(
            intent="ADVICE_REQUEST",
            decision="loop",
            next_stage=None,
            reasons=["User requested advice/solution."],
            extracted={},
            missing={},
            critique="ADVICE_BLOCK"
        )
    
    # ====================
    # 1.4: STAGE GATES (Check if user met requirements)
    # ====================
    # CRITICAL: Gates run BEFORE CLARIFY/METHODOLOGY detection!
    # Why? If user gives valid answer that happens to contain keywords like "מה" or "מהי",
    # it's still a VALID ANSWER, not a question!
    # Only if Gate FAILS, then check if it's a question/clarification.
    
    # ====================================
    # S2 SPECIAL: LLM JUDGE (instead of deterministic gate)
    # ====================================
    # For S2, we use LLM to judge specificity instead of check_gate
    # because LLM is more accurate and generic than deterministic patterns
    
    logger.warning(f"🔍 [ROUTER PRE-CHECK] stg={stg}, StageId.S2={StageId.S2}, match={stg == StageId.S2}")
    
    if stg == StageId.S2:
        logger.warning(f"🎯 [S2 GATE ACTIVATED] Evaluating event specificity via LLM for: '{user_message[:80]}...'")
        
        judge_prompt = f"""You are evaluating if a user's response describes a SPECIFIC EVENT or just a general pattern/situation.

User said: "{user_message}"

ACCEPT if the response describes:
- A single event/interaction (even if time is implicit)
- What actually happened with someone (actions, dialogue, outcome)
- Enough to understand what went wrong or what the challenge was

REJECT only if:
- Just describing a general pattern ("אני תמיד...", "זה קורה לי הרבה")
- No actual event happened ("לא יצאתי", "לא עשיתי כלום")
- Too vague to understand anything ("זה היה נורא" with no details)

Examples of ACCEPT (SPECIFIC EVENT):
✓ "יצאתי עם מישהי, התרגשתי יותר מדי, עשיתי פשלות וזה נגמר" (event with actions & outcome)
✓ "ניסיתי להשמע חכם ומצחיק אבל לא יצא לי טוב" (specific interaction)
✓ "אתמול בערב יצאתי עם מישהי לבית קפה והתרגשתי" (very detailed)

Examples of REJECT (NOT SPECIFIC):
✗ "בשבוע האחרון לא יצאתי עם מישהי" (didn't happen - NON-EVENT)
✗ "יצאתי שבוע לפני והיה נורא" (too vague - what happened?)
✗ "אני לא מצליח למצוא זוגיות" (general situation, not an event)
✗ "יש לי פרויקט שאני עובד עליו" (general, ongoing, not a specific moment)

Respond ONLY with valid JSON:
{{"is_specific": true/false, "reason": "brief explanation"}}"""
        
        try:
            llm_judge = get_azure_chat_llm(purpose="reasoner")
            response = await llm_judge.ainvoke([
                SystemMessage(content="You are a precise evaluator. Output only valid JSON."),
                HumanMessage(content=judge_prompt)
            ])
            
            # Parse LLM response
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
                logger.info(f"🔁 [ROUTER S2] LOOP - LLM judged event not specific enough")
                return ReasonerDecision(
                    intent="ANSWER_PARTIAL",
                    decision="loop",
                    next_stage=None,
                    reasons=[f"Event not specific enough: {reason}"],
                    extracted={},
                    missing={"needs": ["specific_event_moment"]},
                    critique="S2_NOT_SPECIFIC",
                )
            
            # PASS: Event is specific enough - set ok=True to skip regular gate
            logger.info(f"✅ [ROUTER S2] PASS LLM gate - event is specific")
            ok, extracted, missing = True, {"event_description": user_message}, {}
            
        except Exception as e:
            logger.error(f"[S2 GATE] LLM failed: {e}, falling back to regular gate")
            # Fallback to regular gate if LLM fails
            ok, extracted, missing = check_gate(stg.value, user_message, state)
    else:
        # All other stages: use regular check_gate
        ok, extracted, missing = check_gate(stg.value, user_message, state)
    
    # S3 SPECIAL: Validate emotions if gate didn't pass
    if stg == StageId.S3 and not ok:
        # Parse new emotions from user message
        new_emotions = _simple_emotion_list(user_message)
        
        if new_emotions:
            # Validate each new emotion
            valid_emotions = []
            invalid_emotions = []
            unclear_emotions = []
            
            for emotion in new_emotions:
                classification = await classify_emotion_token(emotion, language)
                
                if classification.label == "EMOTION_VALID":
                    valid_emotions.append(emotion)
                elif classification.label == "NOT_EMOTION":
                    invalid_emotions.append((emotion, classification.reason))
                elif classification.label == "EMOTION_UNCLEAR":
                    unclear_emotions.append((emotion, classification.reason))
            
            # CRITICAL FIX: Only reject if there are NO valid emotions
            # If user says "היה שם כעס" → extract "כעס", ignore "היה", "שם"
            
            # If we found valid emotions, continue with those!
            if valid_emotions:
                # Get existing emotions from state
                existing = state.cognitive_data.event_actual.emotions_list if state.cognitive_data else []
                
                # Merge with new valid emotions
                merged = existing.copy() if existing else []
                for e in valid_emotions:
                    if e not in merged:
                        merged.append(e)
                
                # Check if we have enough now (RELAXED: 3 instead of 4)
                if len(merged) >= 3:
                    logger.info(f"[ROUTER S3] ANSWER_OK - found {len(merged)} emotions: {merged}")
                    return ReasonerDecision(
                        intent="ANSWER_OK",
                        decision="advance",
                        next_stage=next_stage(stg).value,
                        reasons=[f"Accumulated {len(merged)} emotions (>=3)."],
                        extracted={"emotions_list": merged},
                        missing={},
                        critique=""
                    )
                else:
                    # Still need more, but we got some valid ones
                    logger.info(f"[ROUTER S3] ANSWER_PARTIAL - accumulated {len(merged)}/{3} emotions")
                    return ReasonerDecision(
                        intent="ANSWER_PARTIAL",
                        decision="loop",
                        next_stage=None,
                        reasons=[f"Accumulated {len(merged)} emotions, need {3-len(merged)} more."],
                        extracted={"emotions_list": merged},
                        missing={"need": 3 - len(merged)},
                        critique=f"Accumulated {len(merged)} emotions, need {3-len(merged)} more."
                    )
            
            # If ALL tokens are invalid (no valid emotions at all)
            if invalid_emotions and not valid_emotions and not unclear_emotions:
                emotion_str = ", ".join([f"'{e[0]}'" for e in invalid_emotions])
                logger.info(f"[ROUTER S3] NOT_EMOTION: {emotion_str}")
                return ReasonerDecision(
                    intent="S3_NOT_EMOTION",
                    decision="loop",
                    next_stage=None,
                    reasons=[f"Not emotions: {emotion_str}"],
                    extracted={},
                    missing={"valid_emotions": True, "invalid_tokens": [e[0] for e in invalid_emotions]},
                    critique=f"S3_NOT_EMOTION: {invalid_emotions[0][1]}"  # Use first reason
                )
            
            # If there are ONLY unclear emotions (no valid, no invalid)
            if unclear_emotions and not valid_emotions:
                emotion_str = ", ".join([f"'{e[0]}'" for e in unclear_emotions])
                logger.info(f"[ROUTER S3] EMOTION_UNCLEAR: {emotion_str}")
                return ReasonerDecision(
                    intent="S3_UNCLEAR_EMOTION",
                    decision="loop",
                    next_stage=None,
                    reasons=[f"Unclear emotions: {emotion_str}"],
                    extracted={},
                    missing={"clarify_emotions": [e[0] for e in unclear_emotions]},
                    critique=f"S3_UNCLEAR_EMOTION: {unclear_emotions[0][0]}"  # Token name
                )
    
    if ok:
        # Gate passed!
        logger.info(f"[ROUTER {stg.value}] ANSWER_OK - gate passed")
        return ReasonerDecision(
            intent="ANSWER_OK",
            decision="advance",
            next_stage=next_stage(stg).value if next_stage(stg) else None,
            reasons=["User met gate requirements."],
            extracted=extracted,
            missing={},
            critique=""
        )
    elif missing:
        # Gate failed with specific missing info
        logger.info(f"[ROUTER {stg.value}] ANSWER_PARTIAL - missing: {missing}")
        
        # ====================
        # LAYER 1.5: Simple OFFTRACK detection (after Gate fails)
        # ====================
        if _detect_offtrack_simple(user_message, language):
            logger.info(f"[ROUTER {stg.value}] OFFTRACK detected (after gate check)")
            return ReasonerDecision(
                intent="OFFTRACK",
                decision="loop",
                next_stage=None,
                reasons=["Input is too short or irrelevant."],
                extracted={},
                missing={},
                critique="OFFTRACK"
            )
        
        # ====================
        # LAYER 1.6: METHODOLOGY QUESTIONS (after Gate fails)
        # ====================
        # Check METHODOLOGY before CLARIFY because it's more specific
        # "מה זה תהליך השיבה?" is methodology, not just clarification
        if _is_methodology_question(user_message, language):
            logger.info(f"[ROUTER {stg.value}] METHODOLOGY_CLARIFY detected (after gate check)")
            return ReasonerDecision(
                intent="METHODOLOGY_CLARIFY",
                decision="loop",
                next_stage=None,
                reasons=["User asked about BSD methodology."],
                extracted={"question": user_message},
                missing={},
                critique="METHODOLOGY_CLARIFY"
            )
        
        # ====================
        # LAYER 1.7: CLARIFY detection (after Gate fails)
        # ====================
        # Check if this is a clarification question ONLY AFTER gate failed (and after methodology check)
        # This prevents false positives: "כלים" contains "מה" but it's not a question
        if _detect_clarification(user_message, language):
            logger.info(f"[ROUTER {stg.value}] CLARIFY detected (after gate check)")
            return ReasonerDecision(
                intent="CLARIFY",
                decision="loop",
                next_stage=None,
                reasons=["User asked for clarification."],
                extracted={},
                missing={},
                critique=f"{stg.value}_CLARIFY"
            )
        
        # ====================
        # LAYER 1.8: GENERIC CRITIQUE (Safety Net)
        # ====================
        # Run Generic Critique to detect if there's a GENERIC issue (too vague, avoidance, etc.)
        # This runs AFTER Stage Gate and AFTER methodology check, as a "safety net" for unclear cases
        
        generic_critique_result = None
        try:
            detector = get_generic_critique_detector()
            stage_req = get_stage_requirement(stg)
            previous_msg = state.conversation_history[-1].get("content", "") if state.conversation_history else None
            
            generic_critique_result = detector.detect(
                user_message=user_message,
                stage=stg,
                stage_requirement=stage_req,
                previous_coach_message=previous_msg
            )
            
            logger.info(
                f"[GENERIC CRITIQUE] {generic_critique_result.label} "
                f"({generic_critique_result.confidence:.2f}) → {generic_critique_result.repair_intent}"
            )
        except Exception as e:
            logger.error(f"[GENERIC CRITIQUE] Failed: {e}")
        
        # Add generic critique info to the ReasonerDecision
        return ReasonerDecision(
            intent="ANSWER_PARTIAL",
            decision="loop",
            next_stage=None,
            reasons=[f"Missing: {', '.join(missing.keys())}"],
            extracted=extracted,
            missing=missing,
            critique="PARTIAL",
            repair_intent=generic_critique_result.repair_intent.value if generic_critique_result else None,
            generic_critique_label=generic_critique_result.label.value if generic_critique_result else None,
            generic_critique_confidence=generic_critique_result.confidence if generic_critique_result else None
        )
    
    # ====================
    # LAYER 2: LLM CLASSIFIER
    # ====================
    
    # Only if Layer 1 didn't decide
    logger.info(f"[ROUTER {stg.value}] Falling back to LLM classifier")
    
    llm = get_azure_chat_llm(purpose="reasoner")
    
    sys = SystemMessage(
        content=(
            "You are an intent classifier for a coaching system.\n"
            "Classify the user's message into ONE of these intents:\n"
            "- ANSWER_OK: User provided relevant answer\n"
            "- ANSWER_PARTIAL: User provided partial answer\n"
            "- OFFTRACK: Irrelevant, joke, or wrong stage\n"
            "\n"
            "Respond with JSON ONLY:\n"
            '{"intent": "ANSWER_OK|ANSWER_PARTIAL|OFFTRACK", "reason": "brief explanation"}\n'
        )
    )
    
    human = HumanMessage(
        content=(
            f"Stage: {stg.value}\n"
            f"Language: {language}\n"
            f"User message: {user_message}\n\n"
            "Classify the intent."
        )
    )
    
    try:
        resp = await llm.ainvoke([sys, human])
        text = (resp.content or "").strip()
        data = json.loads(text)
        
        intent = data.get("intent", "OFFTRACK")
        reason = data.get("reason", "LLM classification")
        
        logger.info(f"[ROUTER {stg.value}] LLM classified: {intent}")
        
        if intent == "ANSWER_OK":
            return ReasonerDecision(
                intent="ANSWER_OK",
                decision="advance",
                next_stage=next_stage(stg).value if next_stage(stg) else None,
                reasons=[reason],
                extracted={},
                missing={},
                critique=""
            )
        elif intent == "ANSWER_PARTIAL":
            return ReasonerDecision(
                intent="ANSWER_PARTIAL",
                decision="loop",
                next_stage=None,
                reasons=[reason],
                extracted={},
                missing={"content": True},
                critique="PARTIAL"
            )
        else:  # OFFTRACK
            return ReasonerDecision(
                intent="OFFTRACK",
                decision="loop",
                next_stage=None,
                reasons=[reason],
                extracted={},
                missing={},
                critique="OFFTRACK"
            )
    
    except Exception as e:
        logger.error(f"[ROUTER ERROR] LLM classifier failed: {e}")
        # Fail-safe: treat as OFFTRACK
        return ReasonerDecision(
            intent="OFFTRACK",
            decision="loop",
            next_stage=None,
            reasons=["Could not classify intent (LLM error)."],
            extracted={},
            missing={},
            critique="OFFTRACK"
        )


# Public API
__all__ = ["route_intent"]

