"""
S1 Router - Specialized routing for Topic stage.

6 Outcomes:
- TOPIC_CLEAR: specific coaching topic → ADVANCE
- GOAL_NOT_TOPIC: goal/aspiration, not a topic → LOOP (ask for topic)
- TOO_BROAD: too general, needs narrowing → LOOP (ask to narrow)
- TOPIC_UNCLEAR: typo/fragment → LOOP (confirm)
- CLARIFY: user asks question → LOOP (explain)
- OFFTRACK: empty/nonsensical → LOOP (ask again)

Architecture: 2-layer routing (deterministic + LLM classifier)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional
import json
import re

from langchain_core.messages import SystemMessage, HumanMessage
from .llm import get_azure_chat_llm
import logging

logger = logging.getLogger(__name__)

S1Intent = Literal["TOPIC_CLEAR", "GOAL_NOT_TOPIC", "TOO_BROAD", "TOPIC_UNCLEAR", "CLARIFY", "OFFTRACK"]


@dataclass
class S1Route:
    """
    Routing decision for S1 (Topic stage).
    
    Attributes:
        intent: The classified intent
        topic_candidate: Extracted topic (may be None if unclear)
        confidence: Confidence score (0.0-1.0)
        rationale: Brief explanation of the decision
    """
    intent: S1Intent
    topic_candidate: Optional[str] = None
    confidence: float = 0.0
    rationale: str = ""


# ==========================================
# LAYER 1: DETERMINISTIC RULES
# ==========================================

def _is_topic_with_approval_request(text: str, language: str) -> Optional[str]:
    """
    Detect if text is a TOPIC + approval request (e.g., "זוגיות זה נושא טוב?").
    
    This is NOT a clarification question - it's a topic proposal with validation request!
    
    Returns:
        Topic candidate if pattern matches, None otherwise
    
    Examples:
        "זוגיות זה נושא טוב?" → "זוגיות"
        "האם זוגיות בסדר?" → "זוגיות"
        "אפשר לדבר על הורות?" → "הורות"
        "Is parenting okay?" → "parenting"
    """
    t = (text or "").strip().lower()
    
    if language == "he":
        # Pattern: "[TOPIC] זה נושא טוב/בסדר?"
        patterns = [
            r"^(.+?)\s+זה\s+נושא\s+(?:טוב|בסדר|מתאים)",
            r"^(.+?)\s+(?:זה\s+)?בסדר",
            r"^(?:האם\s+)?(.+?)\s+(?:זה\s+)?(?:טוב|בסדר|מתאים)",
            r"^אפשר\s+לדבר\s+על\s+(.+)",
            r"^אפשר\s+(.+)",
        ]
    else:
        # Pattern: "is [TOPIC] okay/good/fine?"
        patterns = [
            r"^(.+?)\s+(?:is\s+)?(?:okay|ok|good|fine)",
            r"^is\s+(.+?)\s+(?:okay|ok|good|fine)",
            r"^can\s+(?:we\s+)?(?:talk\s+about\s+)?(.+)",
        ]
    
    for pattern in patterns:
        match = re.search(pattern, t)
        if match:
            topic = match.group(1).strip()
            # Clean common words
            if language == "he":
                topic = topic.replace("האם ", "").replace("אם ", "").strip()
            else:
                topic = topic.replace("is ", "").replace("can ", "").strip()
            
            if len(topic) >= 2:  # Valid topic length
                logger.info(f"[S1] Detected topic with approval request: '{topic}' from '{text}'")
                return topic
    
    return None


def _is_question(text: str, language: str) -> bool:
    """
    Detect if text is a REAL clarification question (CLARIFY intent).
    
    IMPORTANT: Excludes "topic + approval request" patterns!
    
    Checks for:
    - Question mark (but NOT "X זה נושא טוב?")
    - Question words at start
    """
    t = (text or "").strip()
    
    # Check if it's topic + approval request FIRST
    if _is_topic_with_approval_request(t, language):
        return False  # Not a clarification question!
    
    # Has question mark
    if "?" in t or "？" in t:
        return True
    
    # Starts with question word
    if language == "he":
        return t.startswith(("מה", "למה", "איך", "במה", "למה", "מתי", "איפה"))
    else:
        return t.lower().startswith(("what", "why", "how", "when", "where"))


def _looks_offtrack(text: str) -> bool:
    """
    Detect if text is offtrack (empty, numbers only, etc.).
    
    Returns True if:
    - Empty
    - Only numbers/symbols (no letters)
    - Very short (1-2 chars)
    """
    t = (text or "").strip()
    
    # Empty
    if not t:
        return True
    
    # No letters at all (only numbers/symbols)
    if not any(ch.isalpha() for ch in t):
        return True
    
    # Very short (1-2 chars)
    if len(t) <= 2:
        return True
    
    return False


def _looks_unclear_token(text: str) -> bool:
    """
    Detect if text looks like a typo/fragment (TOPIC_UNCLEAR).
    
    Returns True if:
    - Very short (3 chars or less)
    - Repeated characters (e.g., "חחח", "aaaa")
    """
    t = (text or "").strip()
    
    # Very short
    if len(t) <= 3:
        return True
    
    # Repeated characters (3+ times)
    if re.search(r"(.)\1\1", t):
        return True
    
    return False


def _is_broad_topic(topic: str, language: str) -> bool:
    """
    Check if extracted topic is TOO BROAD (needs narrowing).
    
    Examples of broad topics:
    - Hebrew: "זוגיות", "הורות", "עסקים", "עבודה", "משפחה", "חיים", "בריאות"
    - English: "parenting", "relationships", "romance", "business", "work", "family", "life", "health"
    
    Returns True if topic is a single-word domain that needs focus question.
    """
    t = topic.strip().lower()
    
    if language == "he":
        broad_topics_he = {
            "זוגיות", "זוגות", "זוג",
            "הורות", "הורים",
            "עסקים", "עסק", "ביזנס",
            "עבודה",
            "משפחה",
            "חיים",
            "בריאות",
            "יחסים",
            "רומנטיקה",
            "קריירה",
            "כלכלה", "כסף",
            "תקשורת",
            "מנהיגות",
            "חינוך",
        }
        return t in broad_topics_he
    else:
        broad_topics_en = {
            "parenting", "parents",
            "relationships", "relationship",
            "romance", "romantic",
            "business",
            "work",
            "family",
            "life",
            "health",
            "career",
            "money", "finance",
            "communication",
            "leadership",
            "education",
        }
        return t in broad_topics_en


# ==========================================
# LAYER 2: LLM CLASSIFIER
# ==========================================

async def _llm_classify_s1(*, user_message: str, language: str) -> S1Route:
    """
    Use LLM to classify S1 intent when deterministic rules don't decide.
    
    This provides true genericity: model decides if topic is clear/goal/broad without hardcoded word lists.
    """
    llm = get_azure_chat_llm(purpose="reasoner")  # Low temperature
    
    sys = SystemMessage(content=(
        "You are a router for stage S1 of a BSD coaching flow.\n"
        "Task: classify the user's message into exactly ONE of:\n"
        "TOPIC_CLEAR, GOAL_NOT_TOPIC, TOO_BROAD, TOPIC_UNCLEAR, CLARIFY, OFFTRACK.\n"
        "\n"
        "Return ONLY valid JSON with this structure:\n"
        '{"intent": "...", "confidence": 0.0-1.0, "topic_candidate": "...", "rationale": "..."}\n'
        "\n"
        "Definitions:\n"
        "- TOPIC_CLEAR: A SPECIFIC coaching area/domain (not goal, not broad).\n"
        "  ✅ Examples: 'managing anger at kids', 'listening to teenager', 'achieving big goals', 'ניהול כעסים', 'הקשבה לילדים', 'השגת יעדים גדולים'\n"
        "  Characteristics: specific situation/relationship/challenge, actionable, measurable\n"
        "  ✅ 'achieving X' / 'השגת X' / 'dealing with X' = VALID TOPICS (they describe challenge areas)\n"
        "\n"
        "- GOAL_NOT_TOPIC: Extremely vague life aspiration (RARELY used!).\n"
        "  ❌ Examples: 'be happy', 'succeed', 'להיות מאושר', 'להצליח בכלל'\n"
        "  ⚠️  IMPORTANT: 'be a leading father', 'be a good manager', 'אבא מוביל', 'מנהל טוב' = TOPIC_CLEAR!\n"
        "  ⚠️  Only reject if it's EXTREMELY vague like 'be better' / 'succeed in life' with NO specific role/area\n"
        "  Characteristics: no specific role, relationship, or domain mentioned\n"
        "\n"
        "- TOO_BROAD: Too general, needs narrowing.\n"
        "  ⚠️  Examples: 'parenting', 'relationships', 'life', 'הורות', 'יחסים', 'חיים'\n"
        "  Characteristics: one-word domain, could mean 100 different things\n"
        "\n"
        "- TOPIC_UNCLEAR: Complete gibberish that you CANNOT understand AT ALL.\n"
        "  Examples: 'asdfgh', 'חחחחחחח', '12345', random characters\n"
        "  ⚠️  CRITICAL: If you can UNDERSTAND the intent despite typo/spelling → classify as TOO_BROAD or TOPIC_CLEAR!\n"
        "  ✅ Example: 'הורוות' (typo of 'הורות') → TOO_BROAD (you understand it's 'parenting')\n"
        "  ✅ Example: 'parenti' (typo of 'parenting') → TOO_BROAD (you understand it's 'parenting')\n"
        "  ✅ Example: 'רומנטיקה' with any typo → if you understand, accept it!\n"
        "  ❌ Only use TOPIC_UNCLEAR if you TRULY cannot understand what they mean\n"
        "\n"
        "- CLARIFY: User asks what to do / what you mean.\n"
        "  Examples: 'what do you mean?', 'מה הכוונה?'\n"
        "\n"
        "- OFFTRACK: Empty / nonsensical / not answering.\n"
        "  Examples: 'hello', 'היי', '123'\n"
        "\n"
        "Critical Rules:\n"
        "1. TOPIC_CLEAR requires SPECIFICITY - not just a valid word!\n"
        "2. If it's a goal ('want to be X'), return GOAL_NOT_TOPIC\n"
        "3. If it's one general word, return TOO_BROAD\n"
        "4. Be STRICT: most inputs are NOT TOPIC_CLEAR!\n"
    ))
    
    human = HumanMessage(content=f"Language: {language}\nUser message: {user_message}")
    
    try:
        resp = await llm.ainvoke([sys, human])
        text = (resp.content or "").strip()
        
        # Debug logging
        logger.debug(f"[S1 Router] LLM response type: {type(resp)}")
        logger.debug(f"[S1 Router] LLM response content: '{text[:200]}'")
        
        # Clean markdown code blocks (```json ... ```)
        if text.startswith("```"):
            # Remove ```json or ``` from start
            text = re.sub(r"^```(?:json)?\s*\n?", "", text)
            # Remove ``` from end
            text = re.sub(r"\n?```\s*$", "", text)
            text = text.strip()
            logger.debug(f"[S1 Router] Cleaned JSON: '{text[:200]}'")
        
        # Parse JSON
        data = json.loads(text)
        intent = data.get("intent")
        
        # Validate intent
        valid_intents = {"TOPIC_CLEAR", "GOAL_NOT_TOPIC", "TOO_BROAD", "TOPIC_UNCLEAR", "CLARIFY", "OFFTRACK"}
        if intent not in valid_intents:
            raise ValueError(f"Invalid intent: {intent}")
        
        route = S1Route(
            intent=intent,
            confidence=float(data.get("confidence", 0.5)),
            topic_candidate=(data.get("topic_candidate") or "").strip() or None,
            rationale=(data.get("rationale") or "").strip()
        )
        
        logger.info(f"[S1 Router] LLM classified: {route.intent} (confidence={route.confidence:.2f}) - {route.rationale}")
        return route
    
    except Exception as e:
        # Fail closed: if LLM fails, ask for clearer topic
        logger.error(f"[S1 Router] LLM classification failed: {e}")
        return S1Route(
            intent="TOPIC_UNCLEAR",
            confidence=0.2,
            topic_candidate=None,
            rationale="LLM classification error"
        )


# ==========================================
# MAIN ROUTER
# ==========================================

async def route_s1(*, user_message: str, language: str) -> S1Route:
    """
    Main S1 router: combines deterministic rules + LLM classifier.
    
    Flow:
    1. Check if question → CLARIFY
    2. Check if offtrack → OFFTRACK
    3. Check if unclear token → TOPIC_UNCLEAR
    4. Use LLM classifier for final decision
    
    Args:
        user_message: User's message
        language: "he" or "en"
    
    Returns:
        S1Route with intent, topic_candidate, confidence, rationale
    """
    # Layer 1: Deterministic checks
    
    # Check for topic + approval request FIRST (before question check!)
    # Example: "זוגיות זה נושא טוב?" → extract "זוגיות"
    # Then check: is it TOO_BROAD or TOPIC_CLEAR?
    topic_from_approval = _is_topic_with_approval_request(user_message, language)
    if topic_from_approval:
        logger.info(f"[S1 Router] Topic extracted from approval request: '{topic_from_approval}'")
        
        # Check if extracted topic is TOO_BROAD
        if _is_broad_topic(topic_from_approval, language):
            logger.info(f"[S1 Router] TOO_BROAD detected: '{topic_from_approval}' needs narrowing")
            return S1Route(
                intent="TOO_BROAD",
                confidence=0.95,
                topic_candidate=topic_from_approval,
                rationale=f"Broad topic '{topic_from_approval}' needs focus question"
            )
        else:
            logger.info(f"[S1 Router] TOPIC_CLEAR detected: '{topic_from_approval}' is specific")
            return S1Route(
                intent="TOPIC_CLEAR",
                confidence=0.95,
                topic_candidate=topic_from_approval,
                rationale="Specific topic with approval request"
            )
    
    # Check for question (CLARIFY)
    if _is_question(user_message, language):
        logger.info(f"[S1 Router] CLARIFY detected (question)")
        return S1Route(
            intent="CLARIFY",
            confidence=0.9,
            topic_candidate=None,
            rationale="Question detected"
        )
    
    # Check for offtrack
    if _looks_offtrack(user_message):
        logger.info(f"[S1 Router] OFFTRACK detected (empty/non-alpha/too short)")
        return S1Route(
            intent="OFFTRACK",
            confidence=0.9,
            topic_candidate=None,
            rationale="Empty/non-alpha/too short"
        )
    
    # Check for unclear token (save LLM call if obvious typo/fragment)
    if _looks_unclear_token(user_message):
        logger.info(f"[S1 Router] TOPIC_UNCLEAR detected (fragment/typo pattern)")
        return S1Route(
            intent="TOPIC_UNCLEAR",
            confidence=0.8,
            topic_candidate=user_message.strip(),
            rationale="Fragment/typo pattern"
        )
    
    # Layer 2: LLM classifier
    logger.info(f"[S1 Router] Using LLM classifier for: '{user_message}'")
    return await _llm_classify_s1(user_message=user_message, language=language)


# Public API
__all__ = ["S1Route", "S1Intent", "route_s1"]



