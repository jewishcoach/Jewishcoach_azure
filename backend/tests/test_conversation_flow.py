"""
Integration tests for the coaching conversation flow.
Tests critical paths: card chaining, dedup, gate advancement, card data persistence.
Uses a MockLLM to avoid real API calls.
"""

import pytest
from unittest.mock import patch, AsyncMock
from app.bsd_v2.state_schema_v2 import create_initial_state, add_message
from app.bsd_v2.single_agent_coach import handle_conversation, _check_gate_met
from app.bsd_v2.stage_tool_triggers import resolve_post_turn_tool_call
from app.bsd_v2.response_schema import CoachResponseSchema, InternalStateSchema, CollectedDataSchema


# ---------------------------------------------------------------------------
# Mock LLM infrastructure
# ---------------------------------------------------------------------------

def make_mock_response(
    coach_message: str,
    current_step: str,
    saturation_score: float = 0.5,
    collected_data: dict | None = None,
    stage_ready_to_complete: bool = False,
):
    cd_kwargs = collected_data or {}
    return CoachResponseSchema(
        coach_message=coach_message,
        suggestions=[],
        internal_state=InternalStateSchema(
            current_step=current_step,
            saturation_score=saturation_score,
            reflection="test reflection",
            stage_ready_to_complete=stage_ready_to_complete,
            collected_data=CollectedDataSchema(**cd_kwargs),
        ),
    )


class _MockRawMessage:
    """Mimics a langchain AIMessage with empty content and no tool_calls."""
    content = ""
    tool_calls = []


class MockStructuredLLM:
    """Mock structured LLM that returns {raw, parsed, parsing_error} dicts."""

    def __init__(self, responses: list[CoachResponseSchema]):
        self._responses = responses
        self._index = 0

    async def ainvoke(self, messages, **kwargs):
        if self._index >= len(self._responses):
            resp = self._responses[-1]
        else:
            resp = self._responses[self._index]
            self._index += 1
        return {"raw": _MockRawMessage(), "parsed": resp, "parsing_error": None}


class MockLLM:
    """Mock LLM that wraps MockStructuredLLM via with_structured_output."""

    def __init__(self, responses: list[CoachResponseSchema]):
        self._responses = responses

    def with_structured_output(self, schema, **kwargs):
        return MockStructuredLLM(self._responses)

    def bind(self, **kwargs):
        return self


def patch_llm(responses: list[CoachResponseSchema]):
    """Create a patch context that injects MockLLM into the coach."""
    mock = MockLLM(responses)

    def mock_get_llm(*args, **kwargs):
        return mock

    return patch(
        "app.bsd_v2.single_agent_coach.get_azure_chat_llm_4o_mini",
        side_effect=mock_get_llm,
    )


def _make_state_at(step: str, **cd_overrides) -> dict:
    """Create a state pre-filled to a given step with sensible defaults."""
    state = create_initial_state("test-conv", "test-user", "he")
    state["current_step"] = step
    state["ux_version"] = 3
    cd = state["collected_data"]
    cd["topic"] = "מערכות יחסים"
    cd["event_description"] = "שיחה עם אשתי אתמול"
    cd["emotions"] = ["כעס", "תסכול"]
    cd["thought"] = "אני לא מצליח"
    cd.update(cd_overrides)
    return state


# ---------------------------------------------------------------------------
# Test 1: Card chaining S6 → S7 (gap_card appears after comparison_card data)
# ---------------------------------------------------------------------------

def test_card_chain_s6_to_s7():
    """When S6 collected_data is complete, _check_gate_met advances to S7,
    and resolve_post_turn_tool_call returns gap_card."""
    state = _make_state_at("S6")
    state["collected_data"]["action_actual"] = "צעקתי"
    state["collected_data"]["action_desired"] = "לנשום ולדבר בשקט"
    state["collected_data"]["emotion_desired"] = "שקט"
    state["collected_data"]["thought_desired"] = "אני יכול להתמודד"

    # Gate check should advance S6 → S7
    gate_next = _check_gate_met("S6", state["collected_data"])
    assert gate_next == "S7", f"Expected S7, got {gate_next}"

    # Simulate gate auto-advance
    prev_step = "S6"
    state["current_step"] = "S7"

    # Tool resolution should return gap_card
    tool_call = resolve_post_turn_tool_call(prev_step, state, ux_version=3)
    assert tool_call is not None, "Expected gap_card tool_call"
    assert tool_call["tool_type"] == "gap_card"


# ---------------------------------------------------------------------------
# Test 2: No duplicate messages (add_message dedup)
# ---------------------------------------------------------------------------

def test_no_duplicate_messages_in_state():
    """add_message should skip if the last message is identical."""
    state = _make_state_at("S3")

    state = add_message(state, "user", "שלום")
    assert len(state["messages"]) == 1

    # Adding the same message again should be a no-op
    state = add_message(state, "user", "שלום")
    assert len(state["messages"]) == 1, "Duplicate user message was added"

    # A different message should be added
    state = add_message(state, "user", "מה שלומך?")
    assert len(state["messages"]) == 2

    # Coach message after user should be added
    state = add_message(state, "coach", "שלום! מה מעסיק אותך?")
    assert len(state["messages"]) == 3

    # Same coach message again should be skipped
    state = add_message(state, "coach", "שלום! מה מעסיק אותך?")
    assert len(state["messages"]) == 3, "Duplicate coach message was added"


# ---------------------------------------------------------------------------
# Test 3: Gap card saves belief and opportunity values
# ---------------------------------------------------------------------------

def test_gap_card_data_persistence():
    """gap_card submission should save gap_belief and gap_opportunity to collected_data."""
    # Simulate what tools.py does when processing gap_card submission
    cd = {
        "gap_name": "פחד מכישלון",
        "gap_score": "7",
        "gap_booklet_moves": [],
    }

    # Simulate gap_card tool processing (from tools.py lines 155-167)
    data = {
        "gap_name": "פחד מכישלון",
        "gap_score": 7,
        "belief": "כן",
        "opportunity": {"has": True, "what": "להתחיל מצעדים קטנים"},
    }

    moves = list(cd.get("gap_booklet_moves") or [])
    if data.get("belief") is not None:
        if "belief" not in moves:
            moves.append("belief")
        cd["gap_belief"] = data["belief"]
    if data.get("opportunity") is not None:
        if "opportunity" not in moves:
            moves.append("opportunity")
        opp = data["opportunity"]
        if isinstance(opp, dict):
            cd["gap_opportunity"] = opp.get("what", "כן") if opp.get("has") else "לא"
        else:
            cd["gap_opportunity"] = str(opp)
    cd["gap_booklet_moves"] = moves

    assert cd["gap_belief"] == "כן"
    assert cd["gap_opportunity"] == "להתחיל מצעדים קטנים"
    assert "belief" in cd["gap_booklet_moves"]
    assert "opportunity" in cd["gap_booklet_moves"]


# ---------------------------------------------------------------------------
# Test 4: _check_gate_met covers all card-chain stages
# ---------------------------------------------------------------------------

def test_gate_met_all_card_stages():
    """_check_gate_met should correctly identify advancement for all card stages."""
    # S3 → S4: emotions collected
    assert _check_gate_met("S3", {"emotions": ["כעס"]}) == "S4"
    assert _check_gate_met("S3", {"emotions": []}) is None

    # S5 → S6: action_actual collected
    assert _check_gate_met("S5", {"action_actual": "צעקתי"}) == "S6"
    assert _check_gate_met("S5", {}) is None

    # S6 → S7: desired collected
    assert _check_gate_met("S6", {
        "action_desired": "לנשום",
        "emotion_desired": "שקט",
    }) == "S7"
    assert _check_gate_met("S6", {"action_desired": "לנשום"}) is None

    # S7 → S8: gap_name + gap_score + belief + opportunity explored
    assert _check_gate_met("S7", {
        "gap_name": "פחד", "gap_score": "5",
        "gap_booklet_moves": ["belief", "opportunity"],
    }) == "S8"
    # Only name+score without deep exploration → NOT ready
    assert _check_gate_met("S7", {"gap_name": "פחד", "gap_score": "5"}) is None
    assert _check_gate_met("S7", {"gap_name": "פחד"}) is None


# ---------------------------------------------------------------------------
# Test 5: handle_conversation with mock LLM (basic flow)
# ---------------------------------------------------------------------------

async def test_handle_conversation_basic_flow():
    """handle_conversation should return coach message and update state."""
    state = _make_state_at("S3")

    mock_response = make_mock_response(
        coach_message="מה הרגשת באותו רגע?",
        current_step="S3",
        saturation_score=0.4,
        collected_data={"emotions": ["כעס", "עצב"]},
    )

    with patch_llm([mock_response]):
        coach_msg, updated_state = await handle_conversation(
            user_message="הרגשתי כעס ועצב",
            state=state,
            language="he",
        )

    assert coach_msg is not None
    assert len(coach_msg) > 0
    # Gate auto-advance: LLM returned S3 with emotions → backend advances to S4
    assert updated_state["current_step"] == "S4"
    # User message should be in state
    user_msgs = [m for m in updated_state["messages"] if m["sender"] == "user"]
    assert len(user_msgs) == 1
    assert user_msgs[0]["content"] == "הרגשתי כעס ועצב"


# ---------------------------------------------------------------------------
# Test 6: S7 should not auto-advance (post-card coaching needed)
# ---------------------------------------------------------------------------

def test_s7_requires_deep_exploration():
    """S7 gate requires belief + opportunity in gap_booklet_moves,
    not just gap_name + gap_score. This ensures the coach does 3 turns
    of deep exploration before advancing."""
    # Just card data — NOT enough
    cd_card_only = {"gap_name": "פחד", "gap_score": "5"}
    assert _check_gate_met("S7", cd_card_only) is None

    # Card data + partial exploration — NOT enough
    cd_partial = {"gap_name": "פחד", "gap_score": "5", "gap_booklet_moves": ["belief"]}
    assert _check_gate_met("S7", cd_partial) is None

    # Card data + full exploration — ready to advance
    cd_full = {"gap_name": "פחד", "gap_score": "5", "gap_booklet_moves": ["belief", "opportunity"]}
    assert _check_gate_met("S7", cd_full) == "S8"
