"""
Widget Mapper - Maps BSD cognitive data to frontend widget format.

This module bridges the enterprise BSD backend with the smart UI widgets,
providing draft/final status and structured data for each stage.
"""

from typing import Any, Dict, Optional
from .stage_defs import StageId
from .state_schema import CognitiveData


def stage_to_widget_name(stage_id: str) -> str:
    """
    Map BSD stage ID to frontend widget display name.
    
    This determines which widget to render in the frontend.
    """
    mapping = {
        StageId.S1: "Topic",
        StageId.S2: "Event",
        StageId.S3: "Emotions",
        StageId.S4: "Thought",
        StageId.S5: "Action",
        StageId.S6: "Gap",
        StageId.S7: "Pattern",
        StageId.S8: "Being",
        StageId.S9: "KaMaZ",
        StageId.S10: "Commitment",
    }
    try:
        return mapping.get(StageId(stage_id), "Unknown")
    except ValueError:
        return "Unknown"


def get_stage_title(stage_id: str, language: str = "he") -> str:
    """Get display title for a stage."""
    titles = {
        "he": {
            StageId.S1: "נושא האימון",
            StageId.S2: "האירוע",
            StageId.S3: "מסך הרגש",
            StageId.S4: "מסך המחשבה",
            StageId.S5: "מסך המעשה",
            StageId.S6: "ניתוח הפער",
            StageId.S7: "דפוס ופרדיגמה",
            StageId.S8: "בירור הרצון",
            StageId.S9: "כמ\"ז - כוחות",
            StageId.S10: "נוסחת המחויבות",
        },
        "en": {
            StageId.S1: "Coaching Topic",
            StageId.S2: "The Event",
            StageId.S3: "Emotion Screen",
            StageId.S4: "Thought Screen",
            StageId.S5: "Action Screen",
            StageId.S6: "Gap Analysis",
            StageId.S7: "Pattern & Paradigm",
            StageId.S8: "Clarify Desire",
            StageId.S9: "KaMaZ - Forces",
            StageId.S10: "Commitment Formula",
        }
    }
    try:
        stage_key = StageId(stage_id)
        return titles.get(language, titles["he"]).get(stage_key, "Unknown Stage")
    except ValueError:
        return "Unknown Stage"


def extract_widget_data(cognitive_data: CognitiveData, stage_id: str) -> Dict[str, Any]:
    """
    Extract and format data for frontend widgets based on current stage.
    
    Each stage has different data requirements:
    - S3 (Emotions): List of emotions
    - S6 (Gap): Current reality, desired reality
    - S7 (Pattern): Trigger, reaction, consequence
    - S9 (KaMaZ): Source forces, nature forces
    
    Args:
        cognitive_data: The CognitiveData Pydantic model
        stage_id: Current BSD stage ID
    
    Returns:
        Dict formatted for the specific widget
    """
    try:
        stage = StageId(stage_id)
    except ValueError:
        return {}
    
    # S1: Topic
    if stage == StageId.S1:
        return {
            "topic": cognitive_data.topic or ""
        }
    
    # S3: Emotions
    if stage == StageId.S3:
        return {
            "emotions_list": cognitive_data.event_actual.emotions_list or []
        }
    
    # S4: Thought
    if stage == StageId.S4:
        return {
            "thought": cognitive_data.event_actual.thought_content or ""
        }
    
    # S5: Action
    if stage == StageId.S5:
        return {
            "action": cognitive_data.event_actual.action_content or ""
        }
    
    # S6: Gap (uses GapWidget)
    if stage == StageId.S6:
        return {
            "current_reality": f"Gap: {cognitive_data.gap_analysis.name or 'Not defined'}",
            "desired_reality": f"Score: {cognitive_data.gap_analysis.score or 0}/10",
            "gap_name": cognitive_data.gap_analysis.name or "",
            "gap_score": cognitive_data.gap_analysis.score or 0
        }
    
    # S7: Pattern (uses PatternWidget)
    if stage == StageId.S7:
        return {
            "trigger": cognitive_data.pattern_id.name or "",
            "reaction": "User's reaction pattern",  # This might need more extraction
            "consequence": cognitive_data.pattern_id.paradigm or ""
        }
    
    # S8: Being
    if stage == StageId.S8:
        return {
            "identity": cognitive_data.being_desire.identity or ""
        }
    
    # S9: KaMaZ (uses ListWidget)
    if stage == StageId.S9:
        return {
            "source_forces": cognitive_data.kmz_forces.source_forces or [],
            "nature_forces": cognitive_data.kmz_forces.nature_forces or []
        }
    
    # S10: Commitment
    if stage == StageId.S10:
        return {
            "difficulty": cognitive_data.commitment.difficulty or "",
            "result": cognitive_data.commitment.result or ""
        }
    
    return {}


def should_show_widget(stage_id: str, cognitive_data: CognitiveData) -> bool:
    """
    Determine if a stage has enough data to display a widget.
    
    This prevents showing empty widgets for stages that haven't been reached yet.
    """
    try:
        stage = StageId(stage_id)
    except ValueError:
        return False
    
    # Check if stage has any meaningful data
    if stage == StageId.S1:
        return bool(cognitive_data.topic)
    elif stage == StageId.S3:
        return len(cognitive_data.event_actual.emotions_list) > 0
    elif stage == StageId.S4:
        return bool(cognitive_data.event_actual.thought_content)
    elif stage == StageId.S5:
        return bool(cognitive_data.event_actual.action_content)
    elif stage == StageId.S6:
        return bool(cognitive_data.gap_analysis.name)
    elif stage == StageId.S7:
        return bool(cognitive_data.pattern_id.name)
    elif stage == StageId.S8:
        return bool(cognitive_data.being_desire.identity)
    elif stage == StageId.S9:
        return len(cognitive_data.kmz_forces.source_forces) > 0 or \
               len(cognitive_data.kmz_forces.nature_forces) > 0
    elif stage == StageId.S10:
        return bool(cognitive_data.commitment.difficulty)
    
    return False


# Public API
__all__ = [
    "stage_to_widget_name",
    "get_stage_title",
    "extract_widget_data",
    "should_show_widget"
]



