"""
Tests for Insights Builder

Validates that:
1. Insights are built only from cognitive_data (no raw messages)
2. Insights are reflection-only (no interpretation)
3. Invalid insights are rejected
"""

import asyncio
from app.bsd.insights_builder import (
    build_all_insights,
    build_emotion_insights,
    build_gap_insights,
    build_pattern_insights,
    build_identity_insights,
    validate_insight,
    Insight
)
from app.bsd.state_schema import (
    CognitiveData,
    EventActual,
    GapAnalysis,
    PatternId,
    BeingDesire,
    KmzForces,
    Commitment
)


def test_emotion_insights():
    """Test emotion insights are built correctly"""
    cd = CognitiveData(
        event_actual=EventActual(emotions_list=["כעס", "קנאה", "תסכול", "יאוש"])
    )
    
    insights = build_emotion_insights(cd)
    
    assert len(insights) >= 1
    assert any(i.type == "emotion_list" for i in insights)
    assert any(i.source_stage == "S3" for i in insights)
    
    # Check emotion_list insight
    emotion_list_insight = next(i for i in insights if i.type == "emotion_list")
    assert "כעס" in emotion_list_insight.value
    assert emotion_list_insight.metadata["count"] == 4
    
    # Validate
    for insight in insights:
        assert validate_insight(insight, cd) is True
    
    print("✅ Emotion insights test passed")


def test_gap_insights():
    """Test gap insights are built correctly"""
    cd = CognitiveData(
        gap_analysis=GapAnalysis(name="פער בין רצון לפעולה", score=8)
    )
    
    insights = build_gap_insights(cd)
    
    assert len(insights) >= 2
    assert any(i.type == "gap_name" for i in insights)
    assert any(i.type == "gap_intensity" for i in insights)
    
    # Check gap_name insight
    gap_name_insight = next(i for i in insights if i.type == "gap_name")
    assert gap_name_insight.value == "פער בין רצון לפעולה"
    
    # Check gap_intensity insight
    gap_intensity_insight = next(i for i in insights if i.type == "gap_intensity")
    assert gap_intensity_insight.value == "8"
    assert gap_intensity_insight.metadata["level"] == "high"
    
    # Validate
    for insight in insights:
        assert validate_insight(insight, cd) is True
    
    print("✅ Gap insights test passed")


def test_pattern_insights():
    """Test pattern insights are built correctly"""
    cd = CognitiveData(
        pattern_id=PatternId(
            name="דפוס של נסיגה",
            paradigm="אני לא מספיק טוב"
        )
    )
    
    insights = build_pattern_insights(cd)
    
    assert len(insights) == 2
    assert any(i.type == "pattern_name" for i in insights)
    assert any(i.type == "paradigm" for i in insights)
    
    # Validate
    for insight in insights:
        assert validate_insight(insight, cd) is True
    
    print("✅ Pattern insights test passed")


def test_identity_insights():
    """Test identity insights are built correctly"""
    cd = CognitiveData(
        being_desire=BeingDesire(identity="אדם שקול ומרכז")
    )
    
    insight = build_identity_insights(cd)
    
    assert insight is not None
    assert insight.type == "identity"
    assert insight.source_stage == "S8"
    assert insight.value == "אדם שקול ומרכז"
    
    # Validate
    assert validate_insight(insight, cd) is True
    
    print("✅ Identity insights test passed")


def test_invalid_insight_rejected():
    """Test that invalid insights are rejected"""
    cd = CognitiveData(
        event_actual=EventActual(emotions_list=["כעס", "קנאה"])
    )
    
    # Valid insight
    valid_insight = Insight(
        type="emotion_list",
        source_stage="S3",
        value="כעס, קנאה",
        metadata={}
    )
    assert validate_insight(valid_insight, cd) is True
    
    # Invalid: missing source_stage
    try:
        invalid_insight = Insight(
            type="emotion_list",
            source_stage="",
            value="כעס, קנאה",
            metadata={}
        )
        validate_insight(invalid_insight, cd)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "source_stage" in str(e)
    
    # Invalid: empty value
    try:
        invalid_insight = Insight(
            type="emotion_list",
            source_stage="S3",
            value="",
            metadata={}
        )
        validate_insight(invalid_insight, cd)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "empty" in str(e)
    
    # Invalid: invented content (not in cognitive_data)
    try:
        invalid_insight = Insight(
            type="emotion_list",
            source_stage="S3",
            value="שמחה, אושר",  # Not in cognitive_data!
            metadata={}
        )
        validate_insight(invalid_insight, cd)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "reflection-only" in str(e)
    
    print("✅ Invalid insight rejection test passed")


def test_build_all_insights():
    """Test building all insights from full cognitive_data"""
    cd = CognitiveData(
        topic="הורות",
        event_actual=EventActual(
            emotions_list=["כעס", "קנאה", "תסכול", "יאוש"],
            thought_content="אני לא מספיק טוב",
            action_content="צעקתי על הילדים"
        ),
        gap_analysis=GapAnalysis(
            name="פער בין רצון לפעולה",
            score=8
        ),
        pattern_id=PatternId(
            name="דפוס של נסיגה",
            paradigm="אני לא יכול"
        ),
        being_desire=BeingDesire(
            identity="אדם שקול ומרכז"
        ),
        kmz_forces=KmzForces(
            source_forces=["אמונה", "אהבה"],
            nature_forces=["סבלנות", "יצירתיות"]
        ),
        commitment=Commitment(
            difficulty="להישאר רגוע",
            result="בית שקט יותר"
        )
    )
    
    insights = build_all_insights(cd)
    
    # Should have insights from multiple stages
    assert len(insights) > 0
    
    # Check we have insights from different stages
    stages = {i.source_stage for i in insights}
    assert "S3" in stages  # Emotions
    assert "S4" in stages  # Thought
    assert "S5" in stages  # Action
    assert "S6" in stages  # Gap
    assert "S7" in stages  # Pattern
    assert "S8" in stages  # Identity
    assert "S9" in stages  # Forces
    assert "S10" in stages  # Commitment
    
    # All insights should be valid (validation happens in build_all_insights)
    for insight in insights:
        assert insight.source_stage
        assert insight.type
        assert insight.value
    
    print(f"✅ Build all insights test passed ({len(insights)} insights)")


if __name__ == "__main__":
    print("Running Insights Builder Tests...\n")
    
    test_emotion_insights()
    test_gap_insights()
    test_pattern_insights()
    test_identity_insights()
    test_invalid_insight_rejected()
    test_build_all_insights()
    
    print("\n🎉 All insights builder tests passed!")



