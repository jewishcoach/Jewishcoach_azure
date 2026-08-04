"""
BSD V2 - Schemas for macro-stage intro questions and stage summaries.

Used for the structured intro flow between macro-stages:
  Stage complete → Summary card → Intro questions → Free chat
"""

from typing import List, Optional, Union
from pydantic import BaseModel, Field


# -- Macro-stage definitions --

MACRO_STAGES = [
    {
        "id": "identification",
        "title_he": "זיהוי",
        "title_en": "Identification",
        "s_start": "S0",
        "s_end": "S8",
        "description_he": "עוצר לדעת כדי לראות מה באמת קורה בי",
        "description_en": "Stopping to know — seeing what's really happening inside",
    },
    {
        "id": "discovery",
        "title_he": "גילוי",
        "title_en": "Discovery",
        "s_start": "S9",
        "s_end": "S11",
        "description_he": "מגלה שיש דרך נוספת להסתכל על המציאות",
        "description_en": "Discovering there's another way to see reality",
    },
    {
        "id": "kamaz",
        "title_he": 'כמ"ז',
        "title_en": "Forces (KMZ)",
        "s_start": "S12",
        "s_end": "S12",
        "description_he": "כוחות מקור וטבע — בונה האמן אישי",
        "description_en": "Source & Nature forces — building a personal identity card",
    },
    {
        "id": "choice",
        "title_he": "בחירה",
        "title_en": "Choice",
        "s_start": "S13",
        "s_end": "S13",
        "description_he": "בוחר מחדש — עמדה, פרדיגמה ודפוס חדשים",
        "description_en": "Choosing anew — a new stance, paradigm, and pattern",
    },
    {
        "id": "vision",
        "title_he": "חזון",
        "title_en": "Vision",
        "s_start": "S14",
        "s_end": "S15",
        "description_he": "בוחר את החיים שאני באמת רוצה לחיות",
        "description_en": "Choosing the life I truly want to live",
    },
]

MACRO_STAGE_IDS = [m["id"] for m in MACRO_STAGES]

# Boundary end-stages: when the LLM reaches these AND signals ready_to_complete,
# the macro-stage is considered done.
MACRO_STAGE_END_STEPS = {m["id"]: m["s_end"] for m in MACRO_STAGES}

# First S-stage of each macro-stage (for advancing after intro answers).
MACRO_STAGE_START_STEPS = {m["id"]: m["s_start"] for m in MACRO_STAGES}


def step_to_macro_stage(step: str) -> Optional[str]:
    """Map an S-stage (e.g. 'S5') to its macro-stage id."""
    step_num = int(step.replace("S", ""))
    for m in MACRO_STAGES:
        start_num = int(m["s_start"].replace("S", ""))
        end_num = int(m["s_end"].replace("S", ""))
        if start_num <= step_num <= end_num:
            return m["id"]
    return None


def get_macro_stage(macro_id: str) -> Optional[dict]:
    """Get macro-stage definition by id."""
    for m in MACRO_STAGES:
        if m["id"] == macro_id:
            return m
    return None


def next_macro_stage(current_macro_id: str) -> Optional[str]:
    """Return the id of the next macro-stage, or None if at the end."""
    try:
        idx = MACRO_STAGE_IDS.index(current_macro_id)
        if idx + 1 < len(MACRO_STAGE_IDS):
            return MACRO_STAGE_IDS[idx + 1]
    except ValueError:
        pass
    return None


# -- Pydantic schemas for the intro questions API --

class IntroAnswerOption(BaseModel):
    id: str = Field(description="Unique option id, e.g. 'opt_1'")
    label: str = Field(description="Display text for the option")
    emoji: Union[str, None] = Field(default=None, description="Optional emoji")


class IntroQuestion(BaseModel):
    id: str = Field(description="Unique question id, e.g. 'q1'")
    prompt: str = Field(description="The question text")
    options: List[IntroAnswerOption] = Field(description="4-6 answer options")
    multi_select: bool = Field(
        default=True,
        description="Whether user can pick multiple options",
    )
    allow_free_text: bool = Field(
        default=True,
        description="Whether user can type a custom answer",
    )


class StageIntroPayload(BaseModel):
    """LLM-generated intro questions for a macro-stage."""
    stage_id: str = Field(description="Macro-stage id, e.g. 'discovery'")
    stage_title: str = Field(description="Localized stage title")
    intro_text: str = Field(description="Warm intro text before the questions")
    questions: List[IntroQuestion] = Field(description="1-3 contextual questions")


class StageSummaryPayload(BaseModel):
    """Summary shown when a macro-stage completes."""
    stage_id: str = Field(description="Completed macro-stage id")
    stage_title: str = Field(description="Localized stage title")
    insights: List[str] = Field(description="2-4 key insights from the completed stage")
    next_stage_id: Union[str, None] = Field(
        default=None,
        description="Next macro-stage id (None if final)",
    )
    next_stage_title: Union[str, None] = Field(
        default=None,
        description="Next macro-stage localized title (None if final)",
    )
