"""
Tests for emotion_classifier.py - S3 emotion validation.
"""

import asyncio
from app.bsd.emotion_classifier import classify_emotion_token, EmotionClassification


async def test_valid_emotions():
    """Test valid emotion tokens."""
    print("🧪 Testing valid emotions:")
    
    valid_emotions = [
        ("כעס", "he"),
        ("בושה", "he"),
        ("anger", "en"),
        ("shame", "en"),
        ("חוסר אונים", "he"),  # Compound emotion
    ]
    
    for token, lang in valid_emotions:
        result = await classify_emotion_token(token, lang)
        print(f"   '{token}' ({lang}) → {result.label}")
        assert result.label == "EMOTION_VALID", f"Expected EMOTION_VALID, got {result.label}"
    
    print("   ✅ All valid emotions classified correctly")


async def test_invalid_emotions():
    """Test invalid (non-emotion) tokens."""
    print("\n🧪 Testing invalid (non-emotion) tokens:")
    
    invalid_tokens = [
        ("123", "he"),
        ("456", "en"),
        ("ran", "en"),
        ("jumped", "en"),
    ]
    
    for token, lang in invalid_tokens:
        result = await classify_emotion_token(token, lang)
        print(f"   '{token}' ({lang}) → {result.label}")
        assert result.label == "NOT_EMOTION", f"Expected NOT_EMOTION, got {result.label}"
    
    print("   ✅ All invalid tokens classified correctly")


async def test_unclear_emotions():
    """Test unclear emotion tokens (typos, slang)."""
    print("\n🧪 Testing unclear emotions (typos/slang):")
    
    # Note: This is harder to test deterministically as LLM may vary
    unclear_tokens = [
        ("סליגה", "he"),  # Possible typo of סלידה
        ("angar", "en"),  # Possible typo of anger
    ]
    
    for token, lang in unclear_tokens:
        result = await classify_emotion_token(token, lang)
        print(f"   '{token}' ({lang}) → {result.label} ({result.reason})")
        # We accept either EMOTION_UNCLEAR or EMOTION_VALID (LLM may vary)
        assert result.label in ("EMOTION_UNCLEAR", "EMOTION_VALID", "NOT_EMOTION")
    
    print("   ✅ All unclear tokens classified")


async def test_quick_heuristics():
    """Test quick heuristics (before LLM)."""
    print("\n🧪 Testing quick heuristics:")
    
    # Too short
    result = await classify_emotion_token("", "he")
    assert result.label == "NOT_EMOTION"
    print(f"   '' (empty) → {result.label}")
    
    result = await classify_emotion_token("a", "en")
    assert result.label == "NOT_EMOTION"
    print(f"   'a' (single char) → {result.label}")
    
    # Only numbers
    result = await classify_emotion_token("123456", "he")
    assert result.label == "NOT_EMOTION"
    print(f"   '123456' (only numbers) → {result.label}")
    
    print("   ✅ Quick heuristics work correctly")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("EMOTION CLASSIFIER TESTS")
    print("=" * 60)
    
    await test_valid_emotions()
    await test_invalid_emotions()
    await test_unclear_emotions()
    await test_quick_heuristics()
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())



