"""
Jewish Coaching (BSD) - Data Schemas
Multi-Language Support: English Keys, Hebrew Content

This module defines the Pydantic models for structured extraction
of coaching insights from source texts.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class CoachingPhase(str, Enum):
    """
    The phases of the Jewish Coaching methodology.
    English keys for system processing.
    """
    SITUATION = "Situation"
    GAP = "Gap"
    PATTERN = "Pattern"
    PARADIGM = "Paradigm"
    STANCE = "Stance"
    KMZ_SOURCE_NATURE = "KMZ_Source_Nature"
    NEW_CHOICE = "New_Choice"
    VISION = "Vision"
    PPD_PROJECT = "PPD_Project"
    COACHING_REQUEST = "Coaching_Request"
    GENERAL_CONCEPT = "General_Concept"


class CoachingInsight(BaseModel):
    """
    A single coaching insight extracted from source material.
    
    Supports multi-language: Hebrew content with English metadata.
    """
    phase: CoachingPhase = Field(
        ...,
        description="The coaching phase this insight belongs to (English enum)"
    )
    
    original_term: str = Field(
        ...,
        description="The specific Hebrew term used in the source text (e.g., 'הפער', 'כמ״ז')",
        min_length=1
    )
    
    content_he: str = Field(
        ...,
        description="The full extracted insight, story, or explanation in Hebrew",
        min_length=10
    )
    
    summary_en: str = Field(
        ...,
        description="A concise English translation/summary for AI understanding",
        min_length=10
    )
    
    key_question: Optional[str] = Field(
        None,
        description="A coaching question associated with this phase (Hebrew)"
    )
    
    tool_used: Optional[str] = Field(
        None,
        description="The coaching tool or exercise mentioned (e.g., 'Profit/Loss Table', 'Box Exercise')"
    )
    
    source_file: Optional[str] = Field(
        None,
        description="The source file this insight was extracted from"
    )
    
    page_number: Optional[int] = Field(
        None,
        description="Page number in the source document (if available)"
    )
    
    confidence_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Model's confidence in the extraction (0.0 to 1.0)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "phase": "Gap",
                "original_term": "הפער",
                "content_he": "הפער הוא המרחק בין המצוי לבין הרצוי. זיהוי הפער הוא ההזדמנות לשינוי.",
                "summary_en": "The Gap is the distance between current reality and desired state. Identifying the gap is the opportunity for change.",
                "key_question": "מה הפער בין איפה שאני נמצא לבין איפה שאני רוצה להיות?",
                "tool_used": "Gap Analysis Exercise",
                "source_file": "CoachBook.pdf",
                "page_number": 15,
                "confidence_score": 0.95
            }
        }


class ExtractionBatch(BaseModel):
    """
    A batch of insights extracted from a single chunk of text.
    """
    insights: List[CoachingInsight] = Field(
        default_factory=list,
        description="List of coaching insights found in this chunk"
    )
    
    chunk_metadata: Optional[dict] = Field(
        None,
        description="Metadata about the chunk (position, size, etc.)"
    )


class KnowledgeBase(BaseModel):
    """
    The complete knowledge base - aggregation of all extracted insights.
    """
    version: str = Field(
        default="1.0.0",
        description="Version of the knowledge base schema"
    )
    
    total_insights: int = Field(
        default=0,
        description="Total number of insights extracted"
    )
    
    sources_processed: List[str] = Field(
        default_factory=list,
        description="List of source files processed"
    )
    
    insights: List[CoachingInsight] = Field(
        default_factory=list,
        description="All coaching insights in the knowledge base"
    )
    
    metadata: Optional[dict] = Field(
        None,
        description="Additional metadata (processing date, model used, etc.)"
    )
    
    def add_insights(self, new_insights: List[CoachingInsight]):
        """Add new insights to the knowledge base."""
        self.insights.extend(new_insights)
        self.total_insights = len(self.insights)
    
    def get_insights_by_phase(self, phase: CoachingPhase) -> List[CoachingInsight]:
        """Retrieve all insights for a specific coaching phase."""
        return [insight for insight in self.insights if insight.phase == phase]
    
    def get_insights_by_source(self, source_file: str) -> List[CoachingInsight]:
        """Retrieve all insights from a specific source file."""
        return [insight for insight in self.insights if insight.source_file == source_file]


# Phase Descriptions for Reference (can be used in prompts)
PHASE_DESCRIPTIONS = {
    CoachingPhase.SITUATION: {
        "he": "המצוי - תיאור המציאות הנוכחית לעומת המציאות הרצויה",
        "en": "Current reality vs. desired reality descriptions"
    },
    CoachingPhase.GAP: {
        "he": "הפער - המרחק בין המציאות לרצון. זיהוי ההזדמנות",
        "en": "The gap between reality and desire. Recognition of the opportunity"
    },
    CoachingPhase.PATTERN: {
        "he": "דפוס - התנהגויות או תגובות אוטומטיות חוזרות",
        "en": "Recurring automatic behaviors or reactions"
    },
    CoachingPhase.PARADIGM: {
        "he": "פרדיגמה - מחשבת המעשה הנסתרת המניעה את הדפוס",
        "en": "The hidden 'Action Thought' driving the pattern"
    },
    CoachingPhase.STANCE: {
        "he": "עמדה - תפיסת העולם השורשית. כולל ניתוח רווח והפסד",
        "en": "The root worldview. Includes Profit & Loss analysis"
    },
    CoachingPhase.KMZ_SOURCE_NATURE: {
        "he": "כמ״ז - הבחנה בין המקור (נשמה, ערכים, אמונה) לבין הטבע (אגו, הישרדות)",
        "en": "Distinction between Source (soul, values, faith) and Nature (ego, survival)"
    },
    CoachingPhase.NEW_CHOICE: {
        "he": "התחדשות/בחירה - בחירה בעמדה, פרדיגמה ודפוס חדשים",
        "en": "Choosing a NEW Stance, Paradigm, and Pattern"
    },
    CoachingPhase.VISION: {
        "he": "חזון - כיוון עתידי, שליחות, ייעוד",
        "en": "Future orientation, Mission, Destiny"
    },
    CoachingPhase.PPD_PROJECT: {
        "he": "פפ״ד - פרויקט פריצת דרך - יעדים מדידים ספציפיים",
        "en": "Project Breakthrough - specific measurable goals"
    },
    CoachingPhase.COACHING_REQUEST: {
        "he": "בקשה לאימון - הנוסחה: 'אני מבקש להתאמן על X... כדי להגיע ל-Y...'",
        "en": "The formula: 'I ask to train on X... to achieve Y...'"
    },
    CoachingPhase.GENERAL_CONCEPT: {
        "he": "מושג כללי - תובנות או הסברים שאינם משתייכים לשלב ספציפי",
        "en": "General insights or explanations not tied to a specific phase"
    }
}






