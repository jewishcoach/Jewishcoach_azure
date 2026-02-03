from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

"""
BSD State Schema - Enterprise-grade structured state management.

Uses Pydantic for validation and nested models for cognitive_data.
All cognitive data is structured (not free-form JSON) for reliability.
"""


class EventActual(BaseModel):
    """
    Stage S2-S5: Actual event details (3 screens)
    - emotions_list: List of emotions from S3
    - thought_content: Inner sentence from S4
    - action_content: What they actually did from S5
    """
    emotions_list: List[str] = Field(default_factory=list)
    thought_content: Optional[str] = None
    action_content: Optional[str] = None


class EventDesired(BaseModel):
    """
    Stage S5: Desired state (what they want)
    - action_content: What they would want to do/think/feel in ideal state
    """
    action_content: Optional[str] = None


class GapAnalysis(BaseModel):
    """
    Stage S6: Gap between current and desired state
    - score: 1-10 intensity rating (validated on creation)
    - name: Name given to the gap
    
    Note: Validation happens on model creation, not on field assignment.
    To validate after changes, call model.model_validate(model.model_dump())
    """
    score: Optional[int] = Field(None, ge=1, le=10)
    name: Optional[str] = None


class PatternId(BaseModel):
    """
    Stage S7: Recurring pattern and driving belief
    - name: Name of the pattern
    - paradigm: The "that's how it is" belief
    """
    name: Optional[str] = None
    paradigm: Optional[str] = None


class Stance(BaseModel):
    """
    Stage S8: Stance (עמדה) - Root worldview
    - profit: What they gain from this stance
    - loss: What it costs them
    - description: The stance itself
    """
    description: Optional[str] = None
    profit: Optional[str] = None  # Profit (רווח)
    loss: Optional[str] = None  # Loss (הפסד)


class KmzForces(BaseModel):
    """
    Stage S9: KaMaZ forces (כוחות מקור וטבע)
    - source_forces: Values, faith, beliefs
    - nature_forces: Talents, intellect, skills
    """
    source_forces: List[str] = Field(default_factory=list)
    nature_forces: List[str] = Field(default_factory=list)


class RenewalChoice(BaseModel):
    """
    Stage S11: Renewal & Choice (התחדשות ובחירה)
    - new_stance: New chosen worldview
    - new_paradigm: New action-thought
    - new_pattern: New behavior pattern
    """
    new_stance: Optional[str] = None
    new_paradigm: Optional[str] = None
    new_pattern: Optional[str] = None


class Vision(BaseModel):
    """
    Stage S12: Vision (חזון) - Heart's desire
    - mission: Personal mission (שליחות)
    - destiny: Where they want to go (יעוד)
    - hearts_desire: What they truly want (חפץ הלב)
    """
    mission: Optional[str] = None
    destiny: Optional[str] = None
    hearts_desire: Optional[str] = None


class Commitment(BaseModel):
    """
    Stage S10: Final commitment statement
    - difficulty: What they're training on
    - result: Measurable outcome they commit to
    """
    difficulty: Optional[str] = None
    result: Optional[str] = None


class CognitiveData(BaseModel):
    """
    Structured cognitive data extracted during the session.
    Each nested model corresponds to specific stages.
    
    Updated to match full BSD methodology (11 stages from booklet).
    """
    topic: Optional[str] = None  # S1
    event_actual: EventActual = Field(default_factory=EventActual)  # S2-S5 (actual)
    event_desired: EventDesired = Field(default_factory=EventDesired)  # S5 (desired)
    gap_analysis: GapAnalysis = Field(default_factory=GapAnalysis)  # S6
    pattern_id: PatternId = Field(default_factory=PatternId)  # S7
    stance: Stance = Field(default_factory=Stance)  # S8 (CHANGED from being_desire)
    kmz_forces: KmzForces = Field(default_factory=KmzForces)  # S9
    renewal_choice: RenewalChoice = Field(default_factory=RenewalChoice)  # S11 (NEW)
    vision: Vision = Field(default_factory=Vision)  # S12 (NEW)
    commitment: Commitment = Field(default_factory=Commitment)  # S10 (FINAL)


class Metrics(BaseModel):
    """
    Session metrics for Shehiya algorithm and monitoring.
    
    Enhanced with depth and readiness scoring from old system:
    - shehiya_depth_score: Emotional depth score (0.0-1.0) [legacy]
    - depth_score: AI-evaluated insight depth (0.0-10.0) [NEW]
    - readiness_score: Readiness for stage transition (0.0-10.0) [NEW]
    - loop_count_in_current_stage: Number of loops in current stage
    - insights_count: Number of insights identified in current stage [NEW]
    """
    shehiya_depth_score: float = Field(0.0, ge=0.0, le=1.0)
    depth_score: float = Field(0.0, ge=0.0, le=10.0)  # NEW: AI-evaluated depth
    readiness_score: float = Field(0.0, ge=0.0, le=10.0)  # NEW: Readiness for transition
    loop_count_in_current_stage: int = Field(0, ge=0)
    insights_count: int = Field(0, ge=0)  # NEW: Track insights per stage


class BsdState(BaseModel):
    """
    Complete BSD session state for LangGraph.
    
    User context (name, gender) helps coach adapt tone appropriately.
    
    This state is passed between graph nodes and persisted to DB.
    """
    model_config = {
        "validate_assignment": True,  # Validate on field assignment
        "extra": "forbid",  # Forbid extra fields (strict schema)
    }
    
    session_id: Optional[str] = None
    current_state: str = "S0"
    
    # Structured cognitive data
    cognitive_data: CognitiveData = Field(default_factory=CognitiveData)
    
    # Session metrics
    metrics: Metrics = Field(default_factory=Metrics)
    
    # Transient state (not persisted)
    last_user_message: Optional[str] = None
    last_coach_message: Optional[str] = None
    last_extracted: Dict[str, Any] = Field(default_factory=dict)
    
    # User profile (for personalized responses)
    user_name: Optional[str] = None
    user_gender: Optional[str] = None  # "male", "female", or None
    
    # Opener history (for anti-repetition check)
    recent_openers: List[str] = Field(default_factory=list)


# Public API
__all__ = [
    "BsdState",
    "CognitiveData",
    "EventActual",
    "EventDesired",
    "GapAnalysis",
    "PatternId",
    "Stance",
    "KmzForces",
    "RenewalChoice",
    "Vision",
    "Commitment",
    "Metrics",
    "EventDesired",
    "GapAnalysis",
    "PatternId",
    "BeingDesire",
    "KmzForces",
    "Commitment",
    "Metrics",
]
