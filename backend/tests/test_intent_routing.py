"""
Enterprise Intent Routing Tests

Tests the two-layer routing system:
- Layer 1: Deterministic rules
- Layer 2: LLM classifier (fallback)

Test cases:
1. S0: "לא" → STOP (not loop!)
2. S0: "במה?" → CLARIFY → explanation
3. S3: 3 emotions → ANSWER_PARTIAL (need 1 more)
4. S3: 3 + 1 emotions → ANSWER_OK (advance)
5. S3: "123" → OFFTRACK (invalid input)
6. Any stage: "מה לעשות?" → ADVICE_REQUEST → block
"""

import asyncio
from app.bsd.router import route_intent
from app.bsd.state_schema import BsdState, CognitiveData, Metrics, EventActual
from app.bsd.stage_defs import StageId


async def test_s0_stop():
    """S0: User refuses → STOP (not loop!)"""
    state = BsdState(
        current_state=StageId.S0,
        cognitive_data=CognitiveData(),
        metrics=Metrics()
    )
    
    result = await route_intent(
        stage="S0",
        language="he",
        user_message="לא",
        state=state
    )
    
    assert result.intent == "STOP"
    assert result.decision == "stop"
    assert result.next_stage is None


async def test_s0_clarify():
    """S0: User asks for clarification → CLARIFY → loop"""
    state = BsdState(
        current_state=StageId.S0,
        cognitive_data=CognitiveData(),
        metrics=Metrics()
    )
    
    result = await route_intent(
        stage="S0",
        language="he",
        user_message="במה?",
        state=state
    )
    
    assert result.intent == "CLARIFY"
    assert result.decision == "loop"
    assert result.critique == "S0_CLARIFY"


async def test_s3_partial():
    """S3: Only 2 emotions → ANSWER_PARTIAL (need 2 more)"""
    state = BsdState(
        current_state=StageId.S3,
        cognitive_data=CognitiveData(),
        metrics=Metrics()
    )
    
    result = await route_intent(
        stage="S3",
        language="he",
        user_message="כעס, קנאה",
        state=state
    )
    
    assert result.intent == "ANSWER_PARTIAL"
    assert result.decision == "loop"
    assert result.missing.get("emotions_count") == 2
    assert len(result.extracted.get("emotions_list", [])) == 2


async def test_s3_accumulation():
    """S3: 2 emotions + 2 emotions → ANSWER_OK (accumulated 4)"""
    state = BsdState(
        current_state=StageId.S3,
        cognitive_data=CognitiveData(
            event_actual=EventActual(emotions_list=["כעס", "קנאה"])
        ),
        metrics=Metrics()
    )
    
    result = await route_intent(
        stage="S3",
        language="he",
        user_message="תסכול, יאוש",
        state=state
    )
    
    assert result.intent == "ANSWER_OK"
    assert result.decision == "advance"
    assert len(result.extracted.get("emotions_list", [])) == 4
    assert result.next_stage == "S4"


async def test_s3_offtrack():
    """S3: Numbers/gibberish → OFFTRACK"""
    state = BsdState(
        current_state=StageId.S3,
        cognitive_data=CognitiveData(),
        metrics=Metrics()
    )
    
    result = await route_intent(
        stage="S3",
        language="he",
        user_message="123",
        state=state
    )
    
    assert result.intent == "OFFTRACK"
    assert result.decision == "loop"


async def test_advice_request():
    """Any stage: Advice request → ADVICE_REQUEST → block"""
    state = BsdState(
        current_state=StageId.S1,
        cognitive_data=CognitiveData(),
        metrics=Metrics()
    )
    
    result = await route_intent(
        stage="S1",
        language="he",
        user_message="מה לעשות?",
        state=state
    )
    
    assert result.intent == "ADVICE_REQUEST"
    assert result.decision == "loop"
    assert result.critique == "ADVICE_BLOCK"


async def test_s1_valid_topic():
    """S1: Valid topic → ANSWER_OK"""
    state = BsdState(
        current_state=StageId.S1,
        cognitive_data=CognitiveData(),
        metrics=Metrics()
    )
    
    result = await route_intent(
        stage="S1",
        language="he",
        user_message="אני רוצה להתאמן על קשיים בעבודה",
        state=state
    )
    
    assert result.intent == "ANSWER_OK"
    assert result.decision == "advance"
    assert result.extracted.get("topic") is not None


async def test_s1_truncated_topic():
    """S1: Truncated topic (e.g., 'הורו') → ANSWER_PARTIAL with confirm_topic"""
    state = BsdState(
        current_state=StageId.S1,
        cognitive_data=CognitiveData(),
        metrics=Metrics()
    )
    
    result = await route_intent(
        stage="S1",
        language="he",
        user_message="הורו",
        state=state
    )
    
    assert result.intent == "ANSWER_PARTIAL"
    assert result.decision == "loop"
    assert "confirm_topic" in result.missing
    assert result.extracted.get("topic") == "הורו"  # Captured but needs confirmation


async def test_s6_gap_with_score():
    """S6: Gap name + score → ANSWER_OK"""
    state = BsdState(
        current_state=StageId.S6,
        cognitive_data=CognitiveData(),
        metrics=Metrics()
    )
    
    result = await route_intent(
        stage="S6",
        language="he",
        user_message="פער בין רצון לפעולה, 8",
        state=state
    )
    
    assert result.intent == "ANSWER_OK"
    assert result.decision == "advance"
    assert result.extracted.get("gap_name") is not None
    assert result.extracted.get("gap_score") == 8


if __name__ == "__main__":
    # Run tests manually
    async def run_all():
        print("Running Enterprise Intent Routing Tests...\n")
        
        await test_s0_stop()
        print("✅ S0 STOP test passed")
        
        await test_s0_clarify()
        print("✅ S0 CLARIFY test passed")
        
        await test_s3_partial()
        print("✅ S3 PARTIAL test passed")
        
        await test_s3_accumulation()
        print("✅ S3 ACCUMULATION test passed")
        
        await test_s3_offtrack()
        print("✅ S3 OFFTRACK test passed")
        
        await test_advice_request()
        print("✅ ADVICE_REQUEST test passed")
        
        await test_s1_valid_topic()
        print("✅ S1 VALID TOPIC test passed")
        
        await test_s1_truncated_topic()
        print("✅ S1 TRUNCATED TOPIC test passed")
        
        await test_s6_gap_with_score()
        print("✅ S6 GAP test passed")
        
        print("\n🎉 All tests passed!")
    
    asyncio.run(run_all())

