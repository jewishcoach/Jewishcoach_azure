from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from langgraph.graph import StateGraph, END

from .state_schema import BsdState
from .router import route_intent
from .talker import generate_coach_message

"""
BSD LangGraph - Enterprise-grade state machine for coaching flow.

The graph manages the 11-stage BSD methodology, coordinating between
the Reasoner (invisible validation) and Talker (visible coach).
"""

logger = logging.getLogger(__name__)


async def _node_handle_turn(state: BsdState) -> BsdState:
    """
    Main node that processes one coaching turn.
    
    ENTERPRISE FLOW:
    1. Reasoner validates with CONTINUITY (pass cognitive_data for accumulation!)
    2. Update state and metrics based on decision
    3. Talker generates message (LOOP PROMPT if looping, FULL SCRIPT if advancing)
    
    Returns:
        Updated BsdState with new stage, metrics, and coach message
    """
    language = (state.last_extracted or {}).get("language") or "he"

    # Step 1: Router determines intent WITH STATE (for gates/accumulation!)
    decision = await route_intent(
        stage=state.current_state,
        language=language,
        user_message=state.last_user_message or "",
        state=state,  # ✅ Pass full state for gates!
    )

    # Store decision in state for audit
    state.last_extracted = {
        **(state.last_extracted or {}),
        "gatekeeper": asdict(decision),
    }

    # Determine if we're looping or advancing
    is_loop = decision.decision == "loop"
    old_stage = state.current_state

    # Step 2: Update state based on decision
    logger.info(f"🎯 [GRAPH] Stage: {old_stage}, Intent: {decision.intent}, Decision: {decision.decision}, Next: {decision.next_stage}")
    
    if decision.decision == "advance" and decision.next_stage:
        logger.info(f"✅ Advancing: {state.current_state} → {decision.next_stage}")
        state.current_state = decision.next_stage
        # Reset loop counter when stage changes
        state.metrics.loop_count_in_current_stage = 0
    else:
        logger.info(f"🔁 Looping in {state.current_state} (loop #{state.metrics.loop_count_in_current_stage + 1})")
        state.metrics.loop_count_in_current_stage += 1

    # Calculate missing count for S3 (used in loop prompt formatting)
    missing_count = 1
    if old_stage == "S3" and is_loop:
        accumulated_emotions = decision.extracted.get("emotions_list", [])
        missing_count = max(1, 4 - len(accumulated_emotions))

    # Step 3: Talker generates visible coach message
    # ENTERPRISE: Use loop prompt if looping, full script if advancing
    # NEW: Returns (message, opener) tuple
    # NEW: Passes repair_intent from Generic Critique for dynamic guidance
    coach_message, opener_used = await generate_coach_message(
        stage=state.current_state,  # Use NEW stage (for advance) or same (for loop)
        language=language,
        user_message=state.last_user_message or "",
        user_name=state.user_name,
        user_gender=state.user_gender,
        critique=decision.critique,
        intent=decision.intent,  # ✅ Pass intent for specialized responses
        is_loop=is_loop,  # ✅ Tell Talker to use loop prompt if looping!
        missing_count=missing_count,  # ✅ For S3 formatting
        missing=decision.missing,  # ✅ Pass missing info
        recent_openers=state.recent_openers,  # ✅ Anti-repetition check
        cognitive_data=state.cognitive_data.model_dump() if state.cognitive_data else {},  # ✅ Context!
        state=state,  # ✨ CRITICAL: Pass state for insight analysis!
        repair_intent=decision.repair_intent,  # ✅ NEW: Generic Critique repair intent
        generic_critique_label=decision.generic_critique_label,  # ✅ NEW: Critique label
        generic_critique_confidence=decision.generic_critique_confidence,  # ✅ NEW: Confidence score
        loop_count=state.metrics.loop_count_in_current_stage,  # ✨ NEW: Pass loop count for stuck-loop detection!
    )
    
    state.last_coach_message = coach_message
    
    # Track opener for anti-repetition (keep last 5)
    if opener_used:
        state.recent_openers.append(opener_used)
        if len(state.recent_openers) > 5:
            state.recent_openers = state.recent_openers[-5:]
    
    return state


def build_bsd_graph() -> Any:
    """
    Build the BSD LangGraph state machine.
    
    Current MVP: Single "turn" node that processes one user message.
    Future: Could expand to multiple nodes per stage for complex logic.
    
    Returns:
        Compiled LangGraph that can be invoked with BsdState
    """
    g = StateGraph(BsdState)
    g.add_node("turn", _node_handle_turn)
    g.set_entry_point("turn")
    
    # Always end after one turn (external loop manages multiple turns)
    g.add_conditional_edges("turn", lambda s: END, {END: END})
    
    return g.compile()


# Public API
__all__ = ["build_bsd_graph"]
