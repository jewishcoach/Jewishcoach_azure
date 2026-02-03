"""
Tests for Detection-Validation-Extraction Separation

Validates the critical principle:
Detection → Validation → Extraction (SEPARATE!)

Key test: Even if extraction is partial, if detection passes, gate should ADVANCE.
"""

from app.bsd.stage_gates import (
    check_s2_gate,
    check_s5_gate,
    check_s6_gate,
    detect_action_sequence,
    detect_other_people,
    detect_emotion_words,
    detect_concept_word
)
from app.bsd.state_schema import BsdState, CognitiveData, Metrics


def test_detection_functions():
    """Test detection functions work correctly"""
    
    # Action sequence
    assert detect_action_sequence("ביקשתי מהילדה לשטוף כלים והיא סירבה") is True
    assert detect_action_sequence("כעס") is False
    
    # Other people
    assert detect_other_people("הילדה סירבה") is True
    assert detect_other_people("הלכתי לעבודה") is False
    
    # Emotion words
    assert detect_emotion_words("כעסתי וצעקתי") is True
    assert detect_emotion_words("הלכתי הביתה") is False
    
    # Concept word
    assert detect_concept_word("הורות") is True
    assert detect_concept_word("123") is False
    assert detect_concept_word("פ") is False
    
    print("✅ Detection functions test passed")


def test_s2_gate_advances_on_detection():
    """
    Critical test: S2 should ADVANCE if detection passes,
    even if extraction is partial.
    
    Example: User provides full event story.
    Gate should ADVANCE (not loop asking for more).
    """
    state = BsdState(
        current_state="S2",
        cognitive_data=CognitiveData(),
        metrics=Metrics()
    )
    
    # User provides event with action, people, emotion
    user_message = "ביקשתי מהילדה לשטוף כלים, היא סירבה, כעסתי וצעקתי, והיא עלתה לחדרה"
    
    ok, extracted, missing = check_s2_gate(user_message, state)
    
    # Should ADVANCE (ok=True)
    assert ok is True, "Gate should advance when all elements detected"
    
    # Should have extracted something
    assert "event_description" in extracted
    
    # Should NOT be missing anything
    assert len(missing) == 0
    
    print("✅ S2 advances on detection test passed")


def test_s5_gate_advances_even_with_interpretation():
    """
    Critical test: S5 should ADVANCE even if text has "כי" or "בגלל".
    
    OLD BEHAVIOR: Block if has interpretation markers
    NEW BEHAVIOR: ADVANCE, let Talker reflect and clarify if needed
    """
    state = BsdState(
        current_state="S5",
        cognitive_data=CognitiveData(),
        metrics=Metrics()
    )
    
    # User provides action WITH interpretation
    user_message = "צעקתי כי כעסתי"
    
    ok, extracted, missing = check_s5_gate(user_message, state)
    
    # Should ADVANCE (not block!)
    assert ok is True, "Gate should advance even with interpretation"
    
    # Should have extracted the action
    assert extracted.get("action") == user_message
    
    print("✅ S5 advances with interpretation test passed")


def test_s6_gate_advances_without_score():
    """
    Critical test: S6 should ADVANCE even if only gap name (no score).
    
    OLD BEHAVIOR: Block if no score
    NEW BEHAVIOR: ADVANCE, score is helpful but not required
    """
    state = BsdState(
        current_state="S6",
        cognitive_data=CognitiveData(),
        metrics=Metrics()
    )
    
    # User provides gap name WITHOUT score
    user_message = "פער בין רצון לפעולה"
    
    ok, extracted, missing = check_s6_gate(user_message, state)
    
    # Should ADVANCE
    assert ok is True, "Gate should advance even without score"
    
    # Should have extracted gap name
    assert extracted.get("gap_name") == "פער בין רצון לפעולה"
    
    # Score may be None (that's OK!)
    assert extracted.get("gap_score") is None or isinstance(extracted.get("gap_score"), int)
    
    print("✅ S6 advances without score test passed")


def test_s2_gate_loops_when_missing():
    """
    Test that S2 still LOOPS when elements are genuinely missing.
    """
    state = BsdState(
        current_state="S2",
        cognitive_data=CognitiveData(),
        metrics=Metrics()
    )
    
    # User provides only emotion, no event/people
    user_message = "כעס"
    
    ok, extracted, missing = check_s2_gate(user_message, state)
    
    # Should LOOP (ok=False)
    assert ok is False
    
    # Should indicate what's missing
    assert "event" in missing
    assert "people" in missing
    
    print("✅ S2 loops when missing test passed")


if __name__ == "__main__":
    print("Running Detection-Extraction Separation Tests...\n")
    
    test_detection_functions()
    test_s2_gate_advances_on_detection()
    test_s5_gate_advances_even_with_interpretation()
    test_s6_gate_advances_without_score()
    test_s2_gate_loops_when_missing()
    
    print("\n🎉 All detection-extraction tests passed!")
    print()
    print("Key principle validated:")
    print("  Detection → Validation → Extraction (SEPARATE!)")
    print("  Even if extraction is partial, gate ADVANCES if detection passes.")



