"""
BSD V2 - Structured Output Schema for Coach Response

Uses Pydantic + Azure Structured Outputs (json_schema) to guarantee valid JSON.

IMPORTANT: Dict[str, Any] is NOT compatible with OpenAI strict JSON schema mode.
All fields are explicitly typed so strict=True works correctly.
"""

from typing import List, Optional, Union
from pydantic import BaseModel, Field


class StanceSchema(BaseModel):
    gains: List[str] = Field(default_factory=list, description="מה המתאמן מרוויח מהדפוס")
    losses: List[str] = Field(default_factory=list, description="מה המתאמן מפסיד מהדפוס")


class ForcesSchema(BaseModel):
    source: List[str] = Field(default_factory=list, description="ערכים - מקור הכוח")
    nature: List[str] = Field(default_factory=list, description="יכולות - טבע הכוח")


class EntitySchema(BaseModel):
    """Personal context entities — updated throughout the entire conversation."""
    people: List[str] = Field(
        default_factory=list,
        description="שמות ותפקידי אנשים שהוזכרו. למשל: 'הבוס דניאל', 'אשתי רותי'"
    )
    places: List[str] = Field(
        default_factory=list,
        description="מקומות ספציפיים שהוזכרו. למשל: 'חדר הישיבות', 'הבית', 'המשרד'"
    )
    key_examples: List[str] = Field(
        default_factory=list,
        description="דוגמאות ספציפיות שהמתאמן נתן — שמור בלשונו. למשל: 'כשביקש ממני דוח בלי הודעה'"
    )


class CollectedDataSchema(BaseModel):
    """
    Data collected progressively across BSD stages.
    All fields are optional — only fill fields relevant to the current stage.

    S1:  topic
    S2:  event_description
    S3:  emotions
    S4:  thought
    S5:  action_actual (מצוי — actual action only)
    S6:  action_desired, emotion_desired, thought_desired (רצוי — desired state)
    S7:  gap_name, gap_score
    S8:  pattern
    S9:  stance (gains/losses from the pattern — עמדה: רווחים והפסדים)
    S10: forces (values and abilities — כוחות מקור וטבע)
    S11: renewal (new choice / new stance — בחירה חדשה / עמדה חדשה)
    S12: vision (future picture — חזון)
    S13: commitment (concrete first step — מחויבות / צעד קונקרטי)

    IMPORTANT — stage numbers match the prompt file headers exactly:
      S5=מצוי, S6=רצוי, S7=פער, S8=דפוס, S9=עמדה,
      S10=כוחות, S11=בחירה, S12=חזון, S13=מחויבות
    """
    topic: Union[str, None] = Field(default=None, description="נושא האימון (S1)")
    event_description: Union[str, None] = Field(default=None, description="תיאור האירוע הספציפי (S2)")
    emotions: List[str] = Field(default_factory=list, description="רגשות שהמשתמש הביע (S3)")
    thought: Union[str, None] = Field(default=None, description="המשפט הפנימי / מחשבה (S4)")
    action_actual: Union[str, None] = Field(default=None, description="מה עשה בפועל - מצוי (S5). מלא רק בשלב S5!")
    action_desired: Union[str, None] = Field(default=None, description="מה היה רוצה לעשות - רצוי (S6). מלא רק בשלב S6!")
    emotion_desired: Union[str, None] = Field(default=None, description="איך היה רוצה להרגיש - רצוי (S6). מלא רק בשלב S6!")
    thought_desired: Union[str, None] = Field(default=None, description="מה היה רוצה לחשוב - רצוי (S6). מלא רק בשלב S6!")
    gap_name: Union[str, None] = Field(default=None, description="שם הפער (S7). מלא רק בשלב S7!")
    gap_score: Union[str, None] = Field(default=None, description="ציון הפער 1-10 כמחרוזת (S7). מלא רק בשלב S7!")
    pattern: Union[str, None] = Field(default=None, description="הדפוס החוזר שזוהה (S8). מלא רק בשלב S8!")
    stance: Union[StanceSchema, None] = Field(default=None, description="רווחים והפסדים מהדפוס (S9 — עמדה). מלא רק בשלב S9!")
    forces: Union[ForcesSchema, None] = Field(default=None, description="כוחות מקור וטבע: ערכים ויכולות (S10 — כוחות). מלא רק בשלב S10!")
    renewal: Union[str, None] = Field(default=None, description="עמדה חדשה / בחירה מודעת שהמשתמש ניסח (S11 — בחירה). מלא רק בשלב S11!")
    vision: Union[str, None] = Field(default=None, description="חזון / תמונת עתיד (S12 — חזון). מלא רק בשלב S12!")
    commitment: Union[str, None] = Field(default=None, description="מחויבות קונקרטית / צעד ראשון (S13 — מחויבות). מלא רק בשלב S13!")
    entities: Union[EntitySchema, None] = Field(
        default=None,
        description="ישויות אישיות: שמות אנשים, מקומות, דוגמאות ספציפיות. עדכן בכל תור לאורך כל השיחה! זיכרון הקשר חיוני."
    )


class InternalStateSchema(BaseModel):
    """Internal state the coach must return each turn."""

    current_step: str = Field(
        description="השלב הנוכחי בתהליך לפי מתודת BSD, למשל S0, S1, S2 וכו'"
    )
    saturation_score: float = Field(
        description="ציון בין 0.0 ל-1.0 המייצג את מידת השהייה של המשתמש בשלב"
    )
    reflection: str = Field(
        description="חשיבה פנימית קצרה של המאמן לפני שהוא עונה"
    )
    collected_data: CollectedDataSchema = Field(
        default_factory=CollectedDataSchema,
        description="נתונים שנאספו בשלב הנוכחי. עדכן רק שדות רלוונטיים לשלב הנוכחי.",
    )


class CoachResponseSchema(BaseModel):
    """The complete response the model must return."""

    coach_message: str = Field(
        description="התגובה האמפתית למשתמש (Clean Language). ללא מונחים טכניים."
    )
    internal_state: InternalStateSchema = Field(
        description="מצב פנימי: current_step, saturation_score, reflection, collected_data"
    )
