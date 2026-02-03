"""
Generic Critique Detector - LLM-based detection of avoidance patterns

This module provides a safety net for detecting when users are:
- Being too vague
- Going off-topic
- Avoiding the question
- Using wrong type of response (e.g. emotion instead of thought)

It works ACROSS ALL STAGES and returns structured critique + repair intent.
"""

import json
import logging
from enum import Enum
from typing import Optional
from pydantic import BaseModel

from .llm import get_azure_chat_llm
from .stage_defs import StageId

logger = logging.getLogger(__name__)


class CritiqueLabel(str, Enum):
    """Generic critique labels"""
    TOO_VAGUE = "too_vague"           # "אני מרגיש רע" (no specifics)
    TOO_GENERAL = "too_general"       # "אני רוצה להיות טוב יותר"
    PATTERN = "pattern"               # User is pattern-speaking, not specific
    JUDGMENT = "judgment"             # "זה היה נורא" (judgment, not description)
    WRONG_TYPE = "wrong_type"         # Emotion when thought expected, etc.
    OFF_TOPIC = "off_topic"           # Talking about something unrelated
    AVOIDANCE = "avoidance"           # "אני לא יודע", "אין לי"
    OK = "ok"                         # Response is appropriate


class RepairIntent(str, Enum):
    """What kind of repair/guidance is needed"""
    ASK_EXAMPLE = "ask_example"                    # Need concrete example
    ASK_ONE_SENTENCE = "ask_one_sentence"          # Need single sentence/thought
    ASK_MORE_EMOTIONS = "ask_more_emotions"        # Need more emotions
    ASK_SPECIFIC_ACTION = "ask_specific_action"    # Need concrete action
    ASK_THOUGHT_NOT_ACTION = "ask_thought_not_action"  # Clarify thought vs action
    ASK_EMOTION_NOT_THOUGHT = "ask_emotion_not_thought"  # Clarify emotion vs thought
    REFOCUS = "refocus"                            # Bring back to topic
    ENCOURAGE_TRY = "encourage_try"                # User says "don't know" - encourage
    NONE = "none"                                  # No repair needed


class GenericCritique(BaseModel):
    """Result of generic critique detection"""
    label: CritiqueLabel
    confidence: float  # 0.0 - 1.0
    repair_intent: RepairIntent
    reasoning: str  # Why this critique was chosen (for debugging)


class GenericCritiqueDetector:
    """LLM-based detector for generic user response issues"""
    
    def __init__(self):
        self.llm = get_azure_chat_llm(purpose="generic_critique")
    
    def detect(
        self,
        user_message: str,
        stage: StageId,
        stage_requirement: str,
        previous_coach_message: Optional[str] = None
    ) -> GenericCritique:
        """
        Detect if user response has generic issues
        
        Args:
            user_message: What the user said
            stage: Current coaching stage (S2, S3, etc.)
            stage_requirement: What this stage requires (e.g. "specific event", "emotions")
            previous_coach_message: What the coach asked (optional, for context)
        
        Returns:
            GenericCritique with label, confidence, and repair intent
        """
        prompt = self._build_detection_prompt(
            user_message, stage, stage_requirement, previous_coach_message
        )
        
        try:
            response = self.llm.invoke(prompt)
            result = self._parse_llm_response(response.content)
            logger.info(f"Generic critique: {result.label} ({result.confidence:.2f}) - {result.repair_intent}")
            return result
        except Exception as e:
            logger.error(f"Generic critique detection failed: {e}")
            # Safe fallback
            return GenericCritique(
                label=CritiqueLabel.OK,
                confidence=0.5,
                repair_intent=RepairIntent.NONE,
                reasoning="Detection failed, assuming OK"
            )
    
    def _build_detection_prompt(
        self,
        user_message: str,
        stage: StageId,
        stage_requirement: str,
        previous_coach_message: Optional[str]
    ) -> str:
        """Build the LLM prompt for detection"""
        
        context = ""
        if previous_coach_message:
            context = f"\n**השאלה של המאמן:**\n{previous_coach_message}\n"
        
        return f"""אתה מומחה לזיהוי תגובות של משתמשים בתהליך אימון.

**השלב הנוכחי:** {stage.value}
**מה נדרש בשלב זה:** {stage_requirement}
{context}
**תשובת המשתמש:**
"{user_message}"

---

**המשימה שלך:**
זהה אם יש בעיה **גנרית** בתשובה (עמום, הימנעות, לא רלוונטי).
אל תבדוק אם הדרישות הספציפיות של השלב מולאו - רק בעיות גנריות.

**תוויות אפשריות:**

1. **TOO_VAGUE** - התשובה מעורפלת מדי, חסרים פרטים
   דוגמה: "אני מרגיש רע", "היה אירוע"

2. **TOO_GENERAL** - התשובה כללית/רחבה, לא ספציפית
   דוגמה: "אני רוצה להיות טוב יותר", "תמיד קורה לי"

3. **PATTERN** - המשתמש מדבר על דפוס/כללי, לא על מקרה ספציפי
   דוגמה: "זה תמיד קורה כשאני...", "בדרך כלל אני..."

4. **JUDGMENT** - המשתמש שופט/מעריך, לא מתאר
   דוגמה: "זה היה נורא", "הוא איום ונורא"

5. **WRONG_TYPE** - המשתמש ענה בסוג לא נכון (רגש במקום מחשבה וכו')
   דוגמה: אם נדרשה מחשבה והמשתמש ענה "כעס"

6. **OFF_TOPIC** - המשתמש מדבר על משהו לא קשור
   דוגמה: שואלים על אירוע והוא מדבר על העבודה שלו

7. **AVOIDANCE** - המשתמש מתחמק/אומר שלא יודע
   דוגמה: "אני לא יודע", "אין לי תשובה", "לא זכור"

8. **OK** - התשובה סבירה, אין בעיה גנרית
   (אפשר שיש בעיה ספציפית של השלב, אבל זה לא התפקיד שלך)

---

**Repair Intent** - איזה סוג תיקון נדרש:

- ASK_EXAMPLE - צריך דוגמה קונקרטית
- ASK_ONE_SENTENCE - צריך משפט אחד/מחשבה אחת
- ASK_MORE_EMOTIONS - צריך עוד רגשות
- ASK_SPECIFIC_ACTION - צריך פעולה קונקרטית
- ASK_THOUGHT_NOT_ACTION - להבהיר הבדל בין מחשבה לפעולה
- ASK_EMOTION_NOT_THOUGHT - להבהיר הבדל בין רגש למחשבה
- REFOCUS - להחזיר לנושא
- ENCOURAGE_TRY - לעודד לנסות (כשאומר "לא יודע")
- NONE - אין צורך בתיקון

---

**החזר JSON בלבד:**

```json
{{
  "label": "TOO_VAGUE" | "TOO_GENERAL" | "PATTERN" | "JUDGMENT" | "WRONG_TYPE" | "OFF_TOPIC" | "AVOIDANCE" | "OK",
  "confidence": 0.0-1.0,
  "repair_intent": "ASK_EXAMPLE" | "ASK_ONE_SENTENCE" | ... | "NONE",
  "reasoning": "הסבר קצר למה בחרת בתווית הזו"
}}
```

**חשוב:**
- אם יש ספק - בחר OK
- confidence > 0.7 רק אם אתה ממש בטוח
- reasoning צריך להיות קצר (משפט אחד)
"""
    
    def _parse_llm_response(self, response: str) -> GenericCritique:
        """Parse LLM JSON response into GenericCritique"""
        try:
            # Clean markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
                cleaned = cleaned.strip()
            
            data = json.loads(cleaned)
            
            return GenericCritique(
                label=CritiqueLabel(data["label"].lower()),
                confidence=float(data["confidence"]),
                repair_intent=RepairIntent(data["repair_intent"].lower()),
                reasoning=data.get("reasoning", "")
            )
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}\nResponse: {response}")
            # Safe fallback
            return GenericCritique(
                label=CritiqueLabel.OK,
                confidence=0.5,
                repair_intent=RepairIntent.NONE,
                reasoning="Parse failed, assuming OK"
            )


# Stage requirements for context
STAGE_REQUIREMENTS = {
    StageId.S0: "קבלת רשות להתחיל",
    StageId.S1: "נושא ספציפי לאימון",
    StageId.S2: "אירוע ספציפי אחד עם אנשים",
    StageId.S3: "3-4 רגשות שהתעוררו באירוע",
    StageId.S4: "מחשבה/משפט פנימי אחד",
    StageId.S5: "מעשה קונקרטי שנעשה בפועל",
    StageId.S6: "שם לפער + ציון 1-10",
    StageId.S7: "זיהוי דפוס + אמונה",
    StageId.S8: "זהות רצויה (מי להיות)",
    StageId.S9: "כוחות מקור וטבע",
    StageId.S10: "השלמת בקשה סופית",
}


def get_stage_requirement(stage: StageId) -> str:
    """Get human-readable requirement for a stage"""
    return STAGE_REQUIREMENTS.get(stage, "")

