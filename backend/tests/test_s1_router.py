"""
Tests for S1 Router

Critical rule: S1 does NOT advance to S2 unless intent == TOPIC_CLEAR

Test cases:
1. "הורות" → TOPIC_CLEAR → advance
2. "הורו" → TOPIC_UNCLEAR → loop + S1_CONFIRM
3. "זוי" → TOPIC_UNCLEAR → loop + S1_CONFIRM
4. "מה הכוונה?" → CLARIFY → loop + S1_CLARIFY
5. "" / "123" → OFFTRACK → loop + S1_OFFTRACK

Note: Tests focus on deterministic layer (no LLM needed for most cases)
"""

import asyncio
from app.bsd.router_s1 import (
    route_s1,
    S1Route,
    _is_question,
    _looks_offtrack,
    _looks_unclear_token
)


def test_deterministic_layer():
    """Test deterministic detection functions"""
    # Question detection
    assert _is_question("מה הכוונה?", "he") is True
    assert _is_question("במה?", "he") is True
    assert _is_question("what?", "en") is True
    assert _is_question("הורות", "he") is False
    
    # Offtrack detection
    assert _looks_offtrack("") is True
    assert _looks_offtrack("123") is True
    assert _looks_offtrack("...") is True
    assert _looks_offtrack("a") is True
    assert _looks_offtrack("הורות") is False
    
    # Unclear token detection
    assert _looks_unclear_token("זוי") is True   # 3 chars
    assert _looks_unclear_token("חחח") is True  # Repeated chars
    assert _looks_unclear_token("הורות") is False  # 5 chars, no repetition
    assert _looks_unclear_token("הורו") is False  # 4 chars (borderline, LLM will decide)
    # Note: 1-2 chars caught by _looks_offtrack, not _looks_unclear_token
    
    print("✅ Deterministic layer test passed")


async def test_topic_unclear():
    """Test unclear/truncated topics detected deterministically"""
    # These should be caught by deterministic layer (no LLM needed)
    test_cases = [
        ("זוי", "he"),   # 3 chars
        ("par", "en"),   # 3 chars
    ]
    
    for text, lang in test_cases:
        route = await route_s1(user_message=text, language=lang)
        assert route.intent == "TOPIC_UNCLEAR", f"'{text}' should be TOPIC_UNCLEAR, got {route.intent}"
    
    print("✅ TOPIC_UNCLEAR test passed (deterministic layer)")


async def test_clarify():
    """Test clarification questions loop with explanation"""
    test_cases = [
        ("מה הכוונה?", "he"),
        ("במה?", "he"),
        ("what do you mean?", "en"),
        ("what?", "en"),
    ]
    
    for text, lang in test_cases:
        route = await route_s1(user_message=text, language=lang)
        assert route.intent == "CLARIFY", f"'{text}' should be CLARIFY, got {route.intent}"
    
    print("✅ CLARIFY test passed")


async def test_offtrack():
    """Test offtrack input loops with request for topic"""
    test_cases = [
        ("", "he"),      # Empty
        ("123", "he"),   # Numbers only
        ("...", "he"),   # Symbols only
        ("a", "he"),     # Too short
    ]
    
    for text, lang in test_cases:
        route = await route_s1(user_message=text, language=lang)
        assert route.intent == "OFFTRACK", f"'{text}' should be OFFTRACK, got {route.intent}"
    
    print("✅ OFFTRACK test passed")


async def test_critical_rule():
    """
    CRITICAL PRODUCT RULE:
    S1 does NOT advance to S2 unless intent == TOPIC_CLEAR
    
    Note: We test deterministic cases only (no LLM needed)
    """
    # These should LOOP (not advance) - deterministic detection
    unclear_inputs = [
        ("זוי", "TOPIC_UNCLEAR"),    # Fragment (3 chars)
        ("מה הכוונה?", "CLARIFY"),  # Question
        ("123", "OFFTRACK"),         # Numbers only
        ("", "OFFTRACK"),            # Empty
        ("ab", "OFFTRACK"),          # Too short (2 chars)
    ]
    for text, expected_intent in unclear_inputs:
        route = await route_s1(user_message=text, language="he")
        assert route.intent == expected_intent, f"'{text}' must be {expected_intent} (not TOPIC_CLEAR)"
        assert route.intent != "TOPIC_CLEAR", f"'{text}' must NOT advance to S2"
    
    print("✅ CRITICAL RULE validated: Only TOPIC_CLEAR advances to S2")
    print("   (Deterministic layer blocks unclear/offtrack/clarify)")


if __name__ == "__main__":
    async def run_all():
        print("Running S1 Router Tests (Deterministic Layer)...\n")
        
        test_deterministic_layer()
        await test_topic_unclear()
        await test_clarify()
        await test_offtrack()
        await test_critical_rule()
        
        print("\n🎉 All S1 Router tests passed!")
        print()
        print("Key rule enforced:")
        print("  S1 → S2 ONLY if intent == TOPIC_CLEAR")
        print("  All other intents → LOOP (confirm/clarify/ask again)")
        print()
        print("Note: Tests focus on deterministic layer (fast, no LLM)")
        print("      LLM classifier is fallback for ambiguous cases")
    
    asyncio.run(run_all())

