"""
Tests for opener_generator.py - Dynamic, non-robotic coach openers.
"""

import pytest
from app.bsd.opener_generator import (
    generate_opener,
    _word_count,
    _is_too_similar,
    _is_interpretation,
    _enforce_rules,
    OpenerResult
)


def test_word_count():
    """Test word counting."""
    assert _word_count("Hello world") == 2
    assert _word_count("שמעתי אותך") == 2
    assert _word_count("") == 0
    assert _word_count("One") == 1


def test_is_too_similar():
    """Test repetition detection."""
    recent = [
        "שמעתי אותך. זה היה קשה.",
        "הבנתי. זה מאתגר.",
    ]
    
    # Very similar (>60% overlap)
    assert _is_too_similar("שמעתי אותך. זה קשה.", recent) is True
    
    # Not similar
    assert _is_too_similar("ביקשת מהילדה לשטוף כלים.", recent) is False
    
    # Empty recent list
    assert _is_too_similar("שמעתי אותך.", []) is False


def test_is_interpretation():
    """Test interpretation detection."""
    # Hebrew interpretations
    assert _is_interpretation("נראה שאתה עצוב") is True
    assert _is_interpretation("אני חושב שזה קשה") is True
    assert _is_interpretation("זה אומר שאתה מתוסכל") is True
    
    # English interpretations
    assert _is_interpretation("It seems you are sad") is True
    assert _is_interpretation("I think this is difficult") is True
    
    # Pure reflections (OK)
    assert _is_interpretation("שמעתי אותך") is False
    assert _is_interpretation("ביקשת מהילדה לשטוף כלים") is False
    assert _is_interpretation("I hear you") is False


def test_enforce_rules_max_length():
    """Test max length enforcement (12 words)."""
    result = OpenerResult(
        use_opener=True,
        opener="זה משפט ארוך מאוד שיש בו יותר מ-12 מילים ולכן הוא צריך להיות קטוע",
        style_tag="reflective"
    )
    
    enforced = _enforce_rules(result, [], is_advance=False, stage="S2", language="he")
    
    assert enforced.use_opener is True
    assert _word_count(enforced.opener) <= 12


def test_enforce_rules_repetition():
    """Test repetition blocking."""
    recent = ["שמעתי אותך. זה היה קשה."]
    
    result = OpenerResult(
        use_opener=True,
        opener="שמעתי אותך. זה קשה.",  # Too similar
        style_tag="reflective"
    )
    
    enforced = _enforce_rules(result, recent, is_advance=False, stage="S2", language="he")
    
    # Should disable opener due to repetition
    assert enforced.use_opener is False


def test_enforce_rules_interpretation():
    """Test interpretation blocking."""
    result = OpenerResult(
        use_opener=True,
        opener="נראה שאתה עצוב",  # Interpretation
        style_tag="reflective"
    )
    
    enforced = _enforce_rules(result, [], is_advance=False, stage="S2", language="he")
    
    # Should disable opener due to interpretation
    assert enforced.use_opener is False


def test_enforce_rules_advance_no_opener():
    """Test that advance often doesn't need opener."""
    result = OpenerResult(
        use_opener=False,
        opener="",
        style_tag=""
    )
    
    enforced = _enforce_rules(result, [], is_advance=True, stage="S4", language="he")
    
    # Should keep as no opener
    assert enforced.use_opener is False


def test_s3_emotion_list_format():
    """Test S3 emotion list validation."""
    from app.bsd.opener_generator import _is_emotion_list_format
    
    # Valid formats
    assert _is_emotion_list_format("אני שומע: כעס, בושה.", "he") is True
    assert _is_emotion_list_format("I hear: anger, shame.", "en") is True
    
    # Invalid formats (sentences)
    assert _is_emotion_list_format("בעצמי עליה שהיא מסיעה", "he") is False
    assert _is_emotion_list_format("You asked your daughter", "en") is False


def test_s3_enforcement():
    """Test that S3 enforces emotion list format."""
    # Valid S3 opener
    valid = OpenerResult(
        use_opener=True,
        opener="אני שומע: כעס, בושה.",
        style_tag="emotion_list"
    )
    enforced = _enforce_rules(valid, [], is_advance=False, stage="S3", language="he")
    assert enforced.use_opener is True
    
    # Invalid S3 opener (sentence instead of emotion list)
    invalid = OpenerResult(
        use_opener=True,
        opener="בעצמי עליה שהיא מסיעה לפמוש",
        style_tag="reflective"
    )
    enforced2 = _enforce_rules(invalid, [], is_advance=False, stage="S3", language="he")
    assert enforced2.use_opener is False  # Should be disabled


@pytest.mark.asyncio
async def test_generate_opener_basic():
    """Test basic opener generation (integration test with LLM)."""
    result = await generate_opener(
        user_message="ביקשתי מהילדה לשטוף כלים והיא סירבה",
        language="he",
        stage="S2",
        is_advance=False,
        critique="User provided event",
        recent_openers=[]
    )
    
    # Should return a valid OpenerResult
    assert isinstance(result, OpenerResult)
    assert isinstance(result.use_opener, bool)
    assert isinstance(result.opener, str)
    assert isinstance(result.style_tag, str)
    
    # If opener is used, it should be short
    if result.use_opener:
        assert _word_count(result.opener) <= 12


@pytest.mark.asyncio
async def test_generate_opener_advance_often_skips():
    """Test that advance often skips opener."""
    result = await generate_opener(
        user_message="כעס, בושה, קנאה, תסכול",
        language="he",
        stage="S3",
        is_advance=True,  # Advancing to next stage
        critique="User provided 4 emotions",
        recent_openers=[]
    )
    
    # Advance often doesn't use opener (but not mandatory)
    assert isinstance(result, OpenerResult)
    # We don't enforce use_opener=False, just check it's a valid result


@pytest.mark.asyncio
async def test_generate_opener_with_repetition_check():
    """Test that repetition check works in full flow."""
    recent = [
        "שמעתי אותך. זה היה קשה.",
        "הבנתי. זה מאתגר.",
        "שמעתי את מה ששיתפת."
    ]
    
    result = await generate_opener(
        user_message="כעס",
        language="he",
        stage="S3",
        is_advance=False,
        critique="Need more emotions",
        recent_openers=recent
    )
    
    # If opener is used, it should NOT be too similar to recent ones
    if result.use_opener and result.opener:
        assert not _is_too_similar(result.opener, recent)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

