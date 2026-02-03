from __future__ import annotations

import logging
from typing import Any, Dict, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from .graph import build_bsd_graph
from .repo import get_or_create_bsd_state, update_bsd_state, write_audit_log
from .state_schema import BsdState, CognitiveData
from .insights_builder import build_all_insights

"""
BSD Engine - Enterprise-grade orchestrator for coaching sessions.

Critical: Maintains continuity by loading/persisting cognitive_data across turns.
"""

logger = logging.getLogger(__name__)


class BsdEngine:
    """
    Public entry point for the BSD LangGraph core.

    Responsibilities:
    1. Load persisted state from DB (including cognitive_data for continuity)
    2. Run one graph turn
    3. Persist updated stage + cognitive_data + metrics
    4. Emit coach message + metadata for SSE streaming

    Enterprise behavior:
    - Loads cognitive_data from DB (not starting fresh each turn!)
    - Uses Pydantic validation for data integrity
    - Updates timestamps automatically
    - Writes audit trail
    """

    def __init__(self):
        self._graph = build_bsd_graph()

    async def run_turn(
        self,
        *,
        db: Session,
        conversation_id: int,
        user_message: str,
        language: str,
        user_name: str | None = None,
        user_gender: str | None = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Run one coaching turn through the BSD graph.
        
        Args:
            db: SQLAlchemy session
            conversation_id: ID of the conversation
            user_message: User's message
            language: "he" or "en"
        
        Returns:
            Tuple of (coach_message, metadata)
            
        The engine maintains full continuity by:
        - Loading cognitive_data from previous turns
        - Merging new extractions into existing data
        - Persisting everything back to DB
        """
        db_state = get_or_create_bsd_state(db, conversation_id=conversation_id)

        # Hydrate in-memory state from DB (enterprise: continuity matters!)
        # This ensures we don't lose cognitive_data from previous turns
        try:
            cognitive_data = CognitiveData.model_validate(db_state.cognitive_data or {})
        except Exception as e:
            logger.warning(f"Failed to load cognitive_data from DB: {e}, using empty")
            cognitive_data = CognitiveData()

        state = BsdState(
            current_state=db_state.current_stage or "S0",
            cognitive_data=cognitive_data,  # ✅ Load from DB!
            last_user_message=user_message,
            last_extracted={"language": language},
            user_name=user_name,
            user_gender=user_gender,
        )
        
        logger.warning(f"🎬 [ENGINE] Starting turn for conv={conversation_id}: stage={state.current_state}, user_message='{user_message[:50]}...'")

        # Run graph once
        result = await self._graph.ainvoke(state)
        
        # Validate result with Pydantic
        try:
            new_state = BsdState.model_validate(
                result if isinstance(result, dict) else result.__dict__
            )
        except Exception as e:
            logger.error(f"Failed to validate graph result: {e}")
            # Fallback: use input state with error message
            return "מצטער, היתה שגיאה טכנית.", {
                "bsd_stage": state.current_state,
                "current_phase": state.current_state,
                "phase_changed": False,
            }

        # Extract gatekeeper decision
        gatekeeper = (new_state.last_extracted or {}).get("gatekeeper", {}) or {}
        decision = gatekeeper.get("decision", "loop")
        intent = gatekeeper.get("intent", "UNKNOWN")
        critique = gatekeeper.get("critique", "")
        next_stage = gatekeeper.get("next_stage")
        reasons = gatekeeper.get("reasons") or []
        extracted = gatekeeper.get("extracted") or {}

        # Merge new extractions into cognitive_data
        # We work with Pydantic model to ensure structure, then dump to dict
        cd_model = new_state.cognitive_data
        
        # S3: Emotions (ACCUMULATED - Reasoner already merged them!)
        if extracted.get("emotions_list"):
            cd_model.event_actual.emotions_list = extracted["emotions_list"]
        
        # S1: Topic
        if extracted.get("topic"):
            cd_model.topic = extracted["topic"]
        
        # S4: Thought
        if extracted.get("thought"):
            cd_model.event_actual.thought_content = extracted["thought"]
        
        # S5: Action (actual and desired)
        if extracted.get("action_actual"):
            cd_model.event_actual.action_content = extracted["action_actual"]
        if extracted.get("action_desired"):
            cd_model.event_desired.action_content = extracted["action_desired"]
        # Legacy: support old "action" key for backwards compatibility
        if extracted.get("action") and not extracted.get("action_actual"):
            cd_model.event_actual.action_content = extracted["action"]
        
        # S6: Gap
        if extracted.get("gap_name"):
            cd_model.gap_analysis.name = extracted["gap_name"]
        if extracted.get("gap_score"):
            cd_model.gap_analysis.score = extracted["gap_score"]
        
        # S7: Pattern
        if extracted.get("pattern_name"):
            cd_model.pattern_id.name = extracted["pattern_name"]
        if extracted.get("paradigm"):
            cd_model.pattern_id.paradigm = extracted["paradigm"]
        
        # S8: Being/Identity
        if extracted.get("identity"):
            cd_model.being_desire.identity = extracted["identity"]
        
        # S9: KaMaZ forces
        if extracted.get("source_forces"):
            cd_model.kmz_forces.source_forces = extracted["source_forces"]
        if extracted.get("nature_forces"):
            cd_model.kmz_forces.nature_forces = extracted["nature_forces"]
        
        # S10: Commitment
        if extracted.get("commitment_difficulty"):
            cd_model.commitment.difficulty = extracted["commitment_difficulty"]
        if extracted.get("commitment_result"):
            cd_model.commitment.result = extracted["commitment_result"]

        # Persist everything back to DB with automatic updated_at
        update_bsd_state(
            db,
            db_state,
            current_stage=new_state.current_state,
            cognitive_data=cd_model.model_dump(),  # ✅ Persist merged data
            metrics={
                "loop_count_in_current_stage": new_state.metrics.loop_count_in_current_stage,
                "shehiya_depth_score": new_state.metrics.shehiya_depth_score,
            },
        )

        # Handle STOP decision (S0 only)
        if decision == "stop":
            logger.info(f"🛑 [ENGINE] STOP decision - ending session")
            # Write audit log
            write_audit_log(
                db,
                conversation_id=conversation_id,
                stage=state.current_state,
                decision="stop",
                next_stage=None,
                reasons=reasons,
                extracted={},
                raw_user_message=user_message,
            )
            # Return STOP message (no stage script)
            coach_text = (new_state.last_coach_message or "").strip()
            metadata: Dict[str, Any] = {
                "bsd_stage": db_state.current_stage,
                "current_phase": db_state.current_stage,
                "phase_changed": False,
                "stopped": True,
            }
            return coach_text, metadata
        
        # Audit log (log BEFORE state for accurate stage tracking)
        write_audit_log(
            db,
            conversation_id=conversation_id,
            stage=state.current_state,  # Stage when decision was made
            decision=decision,
            next_stage=next_stage if decision == "advance" else None,
            reasons=reasons,
            extracted=extracted,
            raw_user_message=user_message,
        )

        coach_text = (new_state.last_coach_message or "").strip()

        # Metadata for chat response
        # Note: SmartInsightsPanel handles widget display via polling /insights endpoint
        # No need to send tool_call in SSE (prevents duplication)
        metadata: Dict[str, Any] = {
            "bsd_stage": db_state.current_stage,
            "current_phase": db_state.current_stage,
            "phase_changed": decision == "advance",
            "intent": intent,
            "decision": decision,
            "critique": critique,
        }
        
        return coach_text, metadata


# Public API
__all__ = ["BsdEngine"]
