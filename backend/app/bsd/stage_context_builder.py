"""
Stage-Specific Context Builder

Extracts relevant content from RAG for each BSD stage and builds
stage-specific prompts to inject into the conversational coach.

This makes the coach's responses more natural and stage-appropriate.
"""

from typing import Dict, List, Optional
import logging
from .stage_defs import StageId
from .knowledge_rag import get_rag_service

logger = logging.getLogger(__name__)


# Mapping from StageId to Azure Search phase names
# Note: Some stages don't have direct phase mapping (like Emotion_Screen, Thought_Screen)
# so we rely on keywords instead
STAGE_TO_PHASE_MAPPING = {
    StageId.S0: None,  # No specific phase
    StageId.S1: "Situation",  # Topic/Unloading → המצוי/הרצוי
    StageId.S2: "Situation",  # Isolate Event → אירוע ספציפי
    StageId.S3: None,  # Emotions → No Emotion_Screen in RAG, use keywords
    StageId.S4: "Paradigm",  # Thought → מחשבה/פרדיגמה
    StageId.S5: None,  # Action → No Action_Screen in RAG, use keywords
    StageId.S2_READY: None,  # Readiness → No specific phase
    StageId.S6: "Gap",  # Gap Analysis → פער
    StageId.S7: "Pattern",  # Pattern & Paradigm → דפוס
    StageId.S8: "Stance",  # Stance (Profit & Loss) → עמדה/רווח והפסד
    StageId.S9: "KMZ_Source_Nature",  # KaMaZ → כמ"ז
    StageId.S11: "New_Choice",  # Renewal & Choice → בחירה חדשה
    StageId.S12: "Vision",  # Vision → חזון
    StageId.S10: "Coaching_Request",  # Commitment → בקשה לאימון
}


# Keywords for finding dialogue examples per stage
# These are used when phase mapping doesn't exist or as supplement
STAGE_KEYWORDS = {
    StageId.S1: ["המצוי", "הרצוי", "נושא לאימון"],
    StageId.S2: ["אירוע ספציפי", "סיפור", "למפגש הבא"],
    StageId.S3: ["רגש", "מסך רגשי", "אילו רגשות"],  # No Emotion_Screen phase, rely on keywords
    StageId.S4: ["מחשבה", "מסך מחשבתי", "פרדיגמה"],
    StageId.S5: ["מעשה", "מסך מעשי", "דרך הפעולה"],  # No Action_Screen phase
    StageId.S6: ["פער", "הזדמנות"],
    StageId.S7: ["דפוס", "חוזר"],
    StageId.S8: ["עמדה", "רווח והפסד", "מרוויח"],
    StageId.S9: ["כמ\"ז", "כוחות מקור", "כוחות טבע"],
    StageId.S11: ["בחירה חדשה", "עמדה חדשה", "פרדיגמה חדשה"],
    StageId.S12: ["חזון", "שליחות"],
    StageId.S10: ["בקשה לאימון", "אני מבקש להתאמן"],
}


async def build_stage_context(stage: StageId, language: str = "he") -> Optional[str]:
    """
    Build stage-specific context from RAG for injection into conversational prompt.
    
    Args:
        stage: The current BSD stage
        language: "he" or "en"
    
    Returns:
        Context string to inject, or None if RAG unavailable
    """
    rag = get_rag_service()
    
    if not rag.is_available:
        logger.debug(f"[StageContext] RAG unavailable for {stage}")
        return None
    
    try:
        # Get phase and keywords for this stage
        phase = STAGE_TO_PHASE_MAPPING.get(stage)
        keywords = STAGE_KEYWORDS.get(stage, [])
        
        if not phase and not keywords:
            return None
        
        # Search for relevant content
        results = []
        
        # Search by phase
        if phase:
            phase_results = await _search_by_phase(rag, phase)
            results.extend(phase_results)
        
        # Search by keywords
        for keyword in keywords[:2]:  # Limit to 2 keywords to avoid too many queries
            keyword_results = await rag._keyword_search(keyword)
            results.extend(keyword_results[:3])  # Top 3 per keyword
        
        if not results:
            return None
        
        # Filter and format examples
        examples = _filter_dialogue_examples(results, stage)
        
        if not examples:
            return None
        
        # Build stage-specific prompt
        context = _build_stage_prompt(stage, examples, language)
        
        logger.info(f"✅ [StageContext] Built context for {stage}: {len(examples)} examples")
        return context
        
    except Exception as e:
        logger.error(f"❌ [StageContext] Error building context for {stage}: {e}")
        return None


async def _search_by_phase(rag, phase: str) -> List[Dict]:
    """Search RAG by phase name"""
    try:
        # Azure Search doesn't have phase filter in simple search
        # So we search for phase-related terms
        results = await rag._keyword_search(phase)
        return results[:5]
    except:
        return []


def _filter_dialogue_examples(results: List[Dict], stage: StageId) -> List[str]:
    """
    Filter results to keep relevant examples for coaching guidance.
    
    Looks for (in priority order):
    1. Dialogue snippets ("שאל", "אמר")
    2. Key questions from the book
    3. Tool descriptions
    4. ANY relevant content (as fallback)
    """
    examples = []
    
    for result in results:
        content = result.get('content_he', '')
        key_question = result.get('key_question', '')
        tool_used = result.get('tool_used', '')
        original_term = result.get('original_term', '')
        
        # Priority 1: Dialogue (contains שאל, אמר, השיב)
        if any(word in content for word in ['שאל', 'אמר', 'השיב', 'ענה']):
            excerpt = content[:200].strip()
            if len(excerpt) > 30:
                examples.append(f"📖 {excerpt}...")
                continue
        
        # Priority 2: Key questions from book
        if key_question and len(key_question) > 10:
            examples.append(f"❓ {key_question}")
            continue
        
        # Priority 3: Tool descriptions
        if tool_used and len(content) > 30:
            excerpt = content[:150].strip()
            examples.append(f"🔧 [{tool_used}] {excerpt}...")
            continue
        
        # Priority 4: ANY meaningful content (NEW - more permissive!)
        if len(content) > 15:  # At least 15 chars (lowered threshold for short but meaningful snippets)
            # Check if it's actually relevant (not just noise)
            if original_term and len(original_term) > 2:
                excerpt = content[:150].strip()
                examples.append(f"💡 [{original_term}] {excerpt}...")
    
    # Return top 5 unique examples
    unique_examples = list(dict.fromkeys(examples))  # Remove duplicates
    return unique_examples[:5]


def _build_stage_prompt(stage: StageId, examples: List[str], language: str) -> str:
    """
    Build stage-specific prompt from examples.
    
    Returns formatted context to inject into conversational coach.
    """
    if language == "he":
        return _build_hebrew_prompt(stage, examples)
    else:
        return _build_english_prompt(stage, examples)


def _build_hebrew_prompt(stage: StageId, examples: List[str]) -> str:
    """Build Hebrew stage-specific prompt"""
    
    examples_text = "\n".join(examples)
    
    # Stage-specific guidance
    guidance = {
        StageId.S1: "שאל בפשטות על הנושא. אל תגיד 'זה רחב'. שאל 'מה בזה?'",
        StageId.S2: "בקש אירוע ספציפי - מתי? עם מי? מה קרה?",
        StageId.S3: "בקש רגשות ספציפיים. לפחות 4.",
        StageId.S4: "בקש משפט פנימי - מה חשבת באותו רגע?",
        StageId.S5: "בקש מעשה - מה עשית? ואיך רצית לפעול?",
        StageId.S6: "עזור לזהות הפער - תן לו שם וציון 1-10",
        StageId.S7: "עזור לזהות דפוס חוזר ואמונה",
        StageId.S8: "טבלת רווח והפסד - מה מרוויח? מה מפסיד?",
        StageId.S9: "זהה כוחות מקור (ערכים) וטבע (כישורים)",
        StageId.S11: "עזור לבחור עמדה/פרדיגמה/דפוס חדשים",
        StageId.S12: "עזור לראות חזון - שליחות, יעוד, חפץ הלב",
        StageId.S10: "עזור לנסח בקשת אימון מלאה",
    }
    
    stage_guidance = guidance.get(stage, "")
    
    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 הקשר מהספר - שלב {stage.value}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

דוגמאות מסיפור האימון של צבי ודוד:

{examples_text}

💡 עקרונות לשלב זה:
{stage_guidance}

זכור: דבר כמו צבי - בסקרנות, בחמימות, לא כשאלון.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def _build_english_prompt(stage: StageId, examples: List[str]) -> str:
    """Build English stage-specific prompt"""
    
    examples_text = "\n".join(examples)
    
    # Stage-specific guidance
    guidance = {
        StageId.S1: "Ask simply about their topic. Don't say 'too broad'. Ask 'what about it?'",
        StageId.S2: "Request specific event - when? who? what happened?",
        StageId.S3: "Ask for specific emotions. At least 4.",
        StageId.S4: "Ask for internal sentence - what did you think in that moment?",
        StageId.S5: "Ask for action - what did you do? What did you want to do?",
        StageId.S6: "Help identify the gap - name it and rate 1-10",
        StageId.S7: "Help identify recurring pattern and belief",
        StageId.S8: "Profit & Loss table - what do you gain? What do you lose?",
        StageId.S9: "Identify source forces (values) and nature forces (skills)",
        StageId.S11: "Help choose new stance/paradigm/pattern",
        StageId.S12: "Help see vision - mission, destiny, heart's desire",
        StageId.S10: "Help formulate complete coaching request",
    }
    
    stage_guidance = guidance.get(stage, "")
    
    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Context from Book - Stage {stage.value}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Examples from Tzvi and David's coaching story:

{examples_text}

💡 Principles for this stage:
{stage_guidance}

Remember: Speak like Tzvi - with curiosity and warmth, not like a form.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


# Public API
__all__ = ["build_stage_context"]

