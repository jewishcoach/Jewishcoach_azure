"""
Emotion Classifier - Validates emotion tokens in S3 (Emotion Screen).

Purpose: Detect unclear/invalid emotions without using a fixed dictionary.

Approach:
- Uses cold LLM (Reasoner) to classify tokens
- Returns: EMOTION_VALID | EMOTION_UNCLEAR | NOT_EMOTION
- No hard-coded emotion list (works with slang, typos, personal phrasing)

Examples:
- "כעס" → EMOTION_VALID
- "סליגה" (typo) → EMOTION_UNCLEAR (ask for clarification)
- "123" → NOT_EMOTION (explain what counts as emotion)
"""

import json
import logging
from typing import Literal
from dataclasses import dataclass

from langchain_core.messages import SystemMessage, HumanMessage
from .llm import get_azure_chat_llm

logger = logging.getLogger(__name__)

EmotionLabel = Literal["EMOTION_VALID", "EMOTION_UNCLEAR", "NOT_EMOTION"]


@dataclass
class EmotionClassification:
    """Result from emotion classification."""
    label: EmotionLabel
    reason: str


async def classify_emotion_token(token: str, language: str) -> EmotionClassification:
    """
    Classify whether a token is a valid emotion name.
    
    Args:
        token: The word/phrase to classify (e.g., "כעס", "סליגה", "123")
        language: "he" or "en"
    
    Returns:
        EmotionClassification with label and reason
        
    Labels:
        EMOTION_VALID: Clearly a feeling (anger, shame, fear, sadness...)
        EMOTION_UNCLEAR: Looks like typo/unknown word but could be intended as emotion
        NOT_EMOTION: Not a feeling (numbers, actions, objects)
    
    Examples:
        >>> await classify_emotion_token("כעס", "he")
        EmotionClassification(label="EMOTION_VALID", reason="Common emotion word")
        
        >>> await classify_emotion_token("סליגה", "he")
        EmotionClassification(label="EMOTION_UNCLEAR", reason="Possible typo of סלידה")
        
        >>> await classify_emotion_token("123", "he")
        EmotionClassification(label="NOT_EMOTION", reason="Numbers are not emotions")
    """
    token = (token or "").strip()
    
    # Quick heuristics before LLM
    if not token or len(token) < 2:
        return EmotionClassification(
            label="NOT_EMOTION",
            reason="Too short to be a valid emotion word"
        )
    
    # If only numbers/symbols
    if all(not ch.isalpha() for ch in token):
        return EmotionClassification(
            label="NOT_EMOTION",
            reason="Only numbers/symbols, not an emotion word"
        )
    
    # Use LLM classifier (cold, JSON only)
    llm = get_azure_chat_llm(purpose="reasoner")  # Cold temperature
    
    sys = SystemMessage(content=(
        "You are an emotion classifier for a coaching session.\n"
        "Your job: determine if a user's token is a valid emotion/feeling name.\n"
        "\n"
        "Classification rules:\n"
        "1. EMOTION_VALID: Clearly a feeling/emotion word\n"
        "   - Examples: anger, shame, fear, sadness, joy, frustration\n"
        "   - Hebrew: כעס, בושה, פחד, עצב, שמחה, תסכול\n"
        "   - Includes compound emotions: 'חוסר אונים', 'powerlessness'\n"
        "\n"
        "2. EMOTION_UNCLEAR: Looks like typo/misspelling but could be intended as emotion\n"
        "   - Examples: 'סליגה' (probably meant 'סלידה'), 'angar' (probably 'anger')\n"
        "   - Unknown word that MIGHT be slang/personal term for emotion\n"
        "\n"
        "3. NOT_EMOTION: Not a feeling at all\n"
        "   - Examples: numbers (123, 456), actions (ran, jumped), objects (table, car)\n"
        "   - Descriptions of events: 'she refused', 'he yelled'\n"
        "\n"
        "Important:\n"
        "- If unsure, choose EMOTION_UNCLEAR (allow user to clarify)\n"
        "- Don't be too strict - slang/personal terms can be valid\n"
        "- Compound emotions are valid: 'חוסר אונים', 'bitter disappointment'\n"
        "\n"
        "Return ONLY valid JSON:\n"
        '{"label": "EMOTION_VALID|EMOTION_UNCLEAR|NOT_EMOTION", "reason": "brief explanation"}\n'
    ))
    
    human = HumanMessage(content=(
        f"Language: {language}\n"
        f"Token: {token}\n\n"
        "Classify this token."
    ))
    
    try:
        resp = await llm.ainvoke([sys, human])
        text = (resp.content or "{}").strip()
        
        # Parse JSON
        data = json.loads(text)
        label = data.get("label", "EMOTION_UNCLEAR")
        reason = data.get("reason", "")
        
        # Validate label
        if label not in ("EMOTION_VALID", "EMOTION_UNCLEAR", "NOT_EMOTION"):
            logger.warning(f"Invalid label from LLM: {label}, defaulting to EMOTION_UNCLEAR")
            label = "EMOTION_UNCLEAR"
        
        logger.info(f"Classified '{token}' as {label}: {reason}")
        
        return EmotionClassification(
            label=label,  # type: ignore
            reason=reason
        )
    
    except Exception as e:
        logger.error(f"Emotion classification failed for '{token}': {e}")
        # Fail-safe: treat as unclear (allow user to clarify)
        return EmotionClassification(
            label="EMOTION_UNCLEAR",
            reason="Classification failed, treating as unclear"
        )


async def validate_emotion_list(
    emotions: list[str],
    language: str
) -> tuple[list[str], list[tuple[str, EmotionLabel]]]:
    """
    Validate a list of emotion tokens.
    
    Args:
        emotions: List of emotion tokens to validate
        language: "he" or "en"
    
    Returns:
        (valid_emotions, issues)
        - valid_emotions: List of EMOTION_VALID tokens
        - issues: List of (token, label) for EMOTION_UNCLEAR or NOT_EMOTION
    
    Example:
        >>> await validate_emotion_list(["כעס", "סליגה", "123"], "he")
        (["כעס"], [("סליגה", "EMOTION_UNCLEAR"), ("123", "NOT_EMOTION")])
    """
    valid_emotions = []
    issues = []
    
    for token in emotions:
        classification = await classify_emotion_token(token, language)
        
        if classification.label == "EMOTION_VALID":
            valid_emotions.append(token)
        else:
            issues.append((token, classification.label))
    
    return valid_emotions, issues


# Public API
__all__ = [
    "classify_emotion_token",
    "validate_emotion_list",
    "EmotionClassification",
    "EmotionLabel"
]



