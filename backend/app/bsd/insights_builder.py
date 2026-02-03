"""
Insights Builder - Clean architecture for generating coaching insights.

Receives ONLY:
- cognitive_data (structured data from gates)
- stage_outputs (stage-specific extractions)

Does NOT receive:
- raw messages
- history

Principle: Insights are REFLECTIONS, not interpretations.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from .state_schema import CognitiveData
from .stage_defs import StageId
import logging

logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """
    A single coaching insight.
    
    Attributes:
        type: Type of insight (emotion, pattern, identity, gap, etc.)
        source_stage: Which stage generated this insight
        value: The insight content (must be reflection-only, no interpretation)
        metadata: Additional structured data
    """
    type: str
    source_stage: str
    value: str
    metadata: Dict[str, Any]


def build_emotion_insights(cognitive_data: CognitiveData) -> List[Insight]:
    """
    Build insights from S3 (Emotion Screen).
    
    Returns only factual reflections of what the user identified.
    """
    insights = []
    
    emotions = cognitive_data.event_actual.emotions_list
    if not emotions or len(emotions) == 0:
        return insights
    
    # Main insight: list of emotions (factual reflection)
    insights.append(Insight(
        type="emotion_list",
        source_stage="S3",
        value=", ".join(emotions),
        metadata={
            "count": len(emotions),
            "emotions": emotions
        }
    ))
    
    # Density insight (if >= 4 emotions, it's rich)
    if len(emotions) >= 4:
        insights.append(Insight(
            type="emotion_density",
            source_stage="S3",
            value="high",  # Factual: 4+ emotions = high density
            metadata={
                "count": len(emotions)
            }
        ))
    
    return insights


def build_thought_insight(cognitive_data: CognitiveData) -> Optional[Insight]:
    """
    Build insight from S4 (Thought Screen).
    
    Returns the user's verbatim thought.
    """
    thought = cognitive_data.event_actual.thought_content
    if not thought:
        return None
    
    return Insight(
        type="thought",
        source_stage="S4",
        value=thought,
        metadata={}
    )


def build_action_insight(cognitive_data: CognitiveData) -> Optional[Insight]:
    """
    Build insight from S5 (Action Screen).
    
    Returns the user's factual action description.
    """
    action = cognitive_data.event_actual.action_content
    if not action:
        return None
    
    return Insight(
        type="action",
        source_stage="S5",
        value=action,
        metadata={}
    )


def build_gap_insights(cognitive_data: CognitiveData) -> List[Insight]:
    """
    Build insights from S6 (Gap Analysis).
    
    Returns factual gap data without interpretation.
    """
    insights = []
    
    gap = cognitive_data.gap_analysis
    if not gap.name and not gap.score:
        return insights
    
    # Gap name (factual)
    if gap.name:
        insights.append(Insight(
            type="gap_name",
            source_stage="S6",
            value=gap.name,
            metadata={"score": gap.score}
        ))
    
    # Gap intensity (factual score)
    if gap.score:
        insights.append(Insight(
            type="gap_intensity",
            source_stage="S6",
            value=str(gap.score),
            metadata={
                "score": gap.score,
                "level": "high" if gap.score >= 7 else "medium" if gap.score >= 4 else "low"
            }
        ))
    
    return insights


def build_pattern_insights(cognitive_data: CognitiveData) -> List[Insight]:
    """
    Build insights from S7 (Pattern & Paradigm).
    
    Returns factual pattern data identified by the user.
    """
    insights = []
    
    pattern = cognitive_data.pattern_id
    if not pattern.name and not pattern.paradigm:
        return insights
    
    # Pattern name (factual)
    if pattern.name:
        insights.append(Insight(
            type="pattern_name",
            source_stage="S7",
            value=pattern.name,
            metadata={}
        ))
    
    # Underlying paradigm/belief (factual, user-identified)
    if pattern.paradigm:
        insights.append(Insight(
            type="paradigm",
            source_stage="S7",
            value=pattern.paradigm,
            metadata={}
        ))
    
    return insights


def build_identity_insights(cognitive_data: CognitiveData) -> Optional[Insight]:
    """
    Build insight from S8 (Being/Identity).
    
    Returns the user's desired identity (WHO they want to BE).
    """
    identity = cognitive_data.being_desire.identity
    if not identity:
        return None
    
    return Insight(
        type="identity",
        source_stage="S8",
        value=identity,
        metadata={}
    )


def build_forces_insights(cognitive_data: CognitiveData) -> List[Insight]:
    """
    Build insights from S9 (KaMaZ Forces).
    
    Returns source forces (values, faith) and nature forces (talents, skills).
    """
    insights = []
    
    forces = cognitive_data.kmz_forces
    
    # Source forces (values, faith)
    if forces.source_forces and len(forces.source_forces) > 0:
        insights.append(Insight(
            type="source_forces",
            source_stage="S9",
            value=", ".join(forces.source_forces),
            metadata={"forces": forces.source_forces}
        ))
    
    # Nature forces (talents, skills)
    if forces.nature_forces and len(forces.nature_forces) > 0:
        insights.append(Insight(
            type="nature_forces",
            source_stage="S9",
            value=", ".join(forces.nature_forces),
            metadata={"forces": forces.nature_forces}
        ))
    
    return insights


def build_commitment_insight(cognitive_data: CognitiveData) -> Optional[Insight]:
    """
    Build insight from S10 (Commitment Formula).
    
    Returns the user's final commitment statement.
    """
    commitment = cognitive_data.commitment
    if not commitment.difficulty and not commitment.result:
        return None
    
    # Construct commitment statement
    parts = []
    if commitment.difficulty:
        parts.append(commitment.difficulty)
    if commitment.result:
        parts.append(commitment.result)
    
    value = " → ".join(parts) if len(parts) == 2 else parts[0] if parts else ""
    
    if not value:
        return None
    
    return Insight(
        type="commitment",
        source_stage="S10",
        value=value,
        metadata={
            "difficulty": commitment.difficulty,
            "result": commitment.result
        }
    )


def validate_insight(insight: Insight, cognitive_data: CognitiveData) -> bool:
    """
    Validate that an insight is valid and reflection-only.
    
    Rules:
    1. Must have source_stage
    2. Must have type
    3. Must have non-empty value
    4. Value must be reflection-only (from cognitive_data, not invented)
    
    Args:
        insight: The insight to validate
        cognitive_data: The source cognitive data
    
    Returns:
        True if valid, False otherwise
    
    Raises:
        ValueError if insight is invalid
    """
    # Rule 1: Must have source_stage
    if not insight.source_stage:
        raise ValueError(f"Insight missing source_stage: {insight}")
    
    # Rule 2: Must have type
    if not insight.type:
        raise ValueError(f"Insight missing type: {insight}")
    
    # Rule 3: Must have non-empty value
    if not insight.value or not isinstance(insight.value, str) or len(insight.value.strip()) == 0:
        raise ValueError(f"Insight has empty or invalid value: {insight}")
    
    # Rule 4: Value must be reflection-only (verify it exists in cognitive_data)
    if not is_reflection_only(insight, cognitive_data):
        raise ValueError(f"Insight is not reflection-only (contains interpretation): {insight}")
    
    return True


def is_reflection_only(insight: Insight, cognitive_data: CognitiveData) -> bool:
    """
    Check if an insight is reflection-only (no interpretation).
    
    Strategy: Verify that the insight value comes from cognitive_data.
    """
    value = insight.value.strip().lower()
    stage = insight.source_stage
    
    # Collect all source values from cognitive_data
    source_values = []
    
    if stage == "S3":
        source_values.extend([e.lower() for e in cognitive_data.event_actual.emotions_list])
    elif stage == "S4":
        if cognitive_data.event_actual.thought_content:
            source_values.append(cognitive_data.event_actual.thought_content.lower())
    elif stage == "S5":
        if cognitive_data.event_actual.action_content:
            source_values.append(cognitive_data.event_actual.action_content.lower())
    elif stage == "S6":
        if cognitive_data.gap_analysis.name:
            source_values.append(cognitive_data.gap_analysis.name.lower())
        if cognitive_data.gap_analysis.score:
            source_values.append(str(cognitive_data.gap_analysis.score))
    elif stage == "S7":
        if cognitive_data.pattern_id.name:
            source_values.append(cognitive_data.pattern_id.name.lower())
        if cognitive_data.pattern_id.paradigm:
            source_values.append(cognitive_data.pattern_id.paradigm.lower())
    elif stage == "S8":
        if cognitive_data.being_desire.identity:
            source_values.append(cognitive_data.being_desire.identity.lower())
    elif stage == "S9":
        source_values.extend([f.lower() for f in cognitive_data.kmz_forces.source_forces])
        source_values.extend([f.lower() for f in cognitive_data.kmz_forces.nature_forces])
    elif stage == "S10":
        if cognitive_data.commitment.difficulty:
            source_values.append(cognitive_data.commitment.difficulty.lower())
        if cognitive_data.commitment.result:
            source_values.append(cognitive_data.commitment.result.lower())
    
    # Special case: aggregated values (e.g., "emotion1, emotion2")
    if insight.type in ["emotion_list", "source_forces", "nature_forces"]:
        # These are concatenations, so check each part
        parts = [p.strip().lower() for p in value.split(",")]
        return all(any(p in sv or sv in p for sv in source_values) for p in parts)
    
    # Check if value is in source_values (or vice versa for substring match)
    return any(value in sv or sv in value for sv in source_values) or value in ["high", "medium", "low"]


def build_all_insights(cognitive_data: CognitiveData) -> List[Insight]:
    """
    Build all insights from cognitive_data.
    
    This is the main entry point for insight generation.
    
    Args:
        cognitive_data: Structured coaching data
    
    Returns:
        List of validated insights
    """
    insights = []
    
    # Build insights from each stage
    insights.extend(build_emotion_insights(cognitive_data))
    
    thought_insight = build_thought_insight(cognitive_data)
    if thought_insight:
        insights.append(thought_insight)
    
    action_insight = build_action_insight(cognitive_data)
    if action_insight:
        insights.append(action_insight)
    
    insights.extend(build_gap_insights(cognitive_data))
    insights.extend(build_pattern_insights(cognitive_data))
    
    identity_insight = build_identity_insights(cognitive_data)
    if identity_insight:
        insights.append(identity_insight)
    
    insights.extend(build_forces_insights(cognitive_data))
    
    commitment_insight = build_commitment_insight(cognitive_data)
    if commitment_insight:
        insights.append(commitment_insight)
    
    # Validate all insights
    validated = []
    for insight in insights:
        try:
            validate_insight(insight, cognitive_data)
            validated.append(insight)
            logger.debug(f"✅ Validated insight: {insight.type} from {insight.source_stage}")
        except ValueError as e:
            logger.error(f"❌ Invalid insight rejected: {e}")
            # Do NOT include invalid insights
    
    return validated


# Public API
__all__ = ["Insight", "build_all_insights", "validate_insight"]



