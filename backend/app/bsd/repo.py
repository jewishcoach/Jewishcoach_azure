from __future__ import annotations

import logging
from datetime import datetime
from sqlalchemy.orm import Session

from ..models import BsdSessionState, BsdAuditLog

"""
BSD Repository - Enterprise-grade DB operations for BSD state and audit logs.

Handles persistence of session state and audit trail with proper timestamps.
"""

logger = logging.getLogger(__name__)


def get_or_create_bsd_state(db: Session, *, conversation_id: int) -> BsdSessionState:
    """
    Get existing BSD session state or create a new one.
    
    Args:
        db: SQLAlchemy session
        conversation_id: ID of the conversation
    
    Returns:
        BsdSessionState with initialized values
    
    The state is created with:
    - current_stage: "S0" (consent)
    - cognitive_data: empty dict
    - metrics: initialized to zero
    - timestamps: created_at and updated_at
    """
    state = (
        db.query(BsdSessionState)
        .filter(BsdSessionState.conversation_id == conversation_id)
        .first()
    )
    if state:
        logger.warning(f"🔄 [BSD REPO] Found EXISTING state for conversation {conversation_id}: stage={state.current_stage}")
        return state

    # Create new state with enterprise defaults
    now = datetime.utcnow()
    state = BsdSessionState(
        conversation_id=conversation_id,
        current_stage="S0",
        cognitive_data={},
        metrics={
            "loop_count_in_current_stage": 0,
            "shehiya_depth_score": 0.0,
        },
        created_at=now,
        updated_at=now,
    )
    db.add(state)
    db.commit()
    db.refresh(state)
    
    logger.warning(f"✨ [BSD REPO] Created NEW BSD state for conversation {conversation_id}: stage=S0")
    return state


def update_bsd_state(
    db: Session,
    state: BsdSessionState,
    *,
    current_stage: str | None = None,
    cognitive_data: dict | None = None,
    metrics: dict | None = None,
) -> BsdSessionState:
    """
    Update BSD session state with proper timestamp management.
    
    Args:
        db: SQLAlchemy session
        state: State object to update
        current_stage: New stage (if changing)
        cognitive_data: Updated cognitive data
        metrics: Updated metrics
    
    Returns:
        Updated BsdSessionState
    
    Always updates the updated_at timestamp.
    """
    if current_stage is not None:
        state.current_stage = current_stage
    
    if cognitive_data is not None:
        state.cognitive_data = cognitive_data
    
    if metrics is not None:
        state.metrics = metrics
    
    # Always update timestamp on any change
    state.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(state)
    
    return state


def write_audit_log(
    db: Session,
    *,
    conversation_id: int,
    stage: str,
    decision: str,
    next_stage: str | None,
    reasons: list[str] | None,
    extracted: dict | None,
    raw_user_message: str | None,
) -> BsdAuditLog:
    """
    Write an audit log entry for a Reasoner decision.
    
    Args:
        db: SQLAlchemy session
        conversation_id: ID of the conversation
        stage: Current stage when decision was made
        decision: "advance" or "loop"
        next_stage: Stage to advance to (if advancing)
        reasons: List of reasons for the decision
        extracted: Structured data extracted from user input
        raw_user_message: Original user message
    
    Returns:
        Created BsdAuditLog entry
    
    The audit log provides a complete trail of all Reasoner decisions
    for system calibration and debugging.
    """
    log = BsdAuditLog(
        conversation_id=conversation_id,
        stage=stage,
        decision=decision,
        next_stage=next_stage,
        reasons=reasons or [],
        extracted=extracted or {},
        raw_user_message=raw_user_message,
        created_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    
    logger.debug(
        f"Audit: conv={conversation_id} stage={stage} "
        f"decision={decision} next={next_stage}"
    )
    
    return log


# Public API
__all__ = [
    "get_or_create_bsd_state",
    "update_bsd_state",
    "write_audit_log",
]
