"""
BSD V2 Chat API Endpoint

Side-by-side with V1 - experimental single-agent architecture.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..dependencies import get_current_user, get_current_admin_user
from ..security.chat_input import (
    MAX_CHAT_MESSAGE_CHARS,
    ChatMessageRejected,
    sanitize_chat_message,
)
from ..middleware.usage_limiter import require_message_quota
from ..bsd_v2.single_agent_coach import handle_conversation, warm_prompt_cache
from ..bsd_v2.state_schema_v2 import create_initial_state
from ..database import get_db
from ..limiter import limiter
from ..models import User, Conversation as ConversationModel, Message
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat/v2", tags=["BSD V2"])


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ══════════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_CHAT_MESSAGE_CHARS)
    conversation_id: int
    language: str = "he"


class ChatResponse(BaseModel):
    coach_message: str
    conversation_id: int
    current_step: str
    saturation_score: float
    tool_call: dict | None = None  # Interactive tool to activate in InsightHub


# Defines which tool to activate when the coach first enters each stage.
# Only stages with interactive input cards are listed here.
_STAGE_TOOL_TRIGGERS: dict[str, dict] = {
    "S11": {
        "type": "tool",
        "tool_type": "profit_loss",
        "title_he": "טבלת רווח והפסד",
        "title_en": "Gain / Loss Table",
        "instruction_he": "מה אתה מרוויח מהדפוס הזה? ומה אתה מפסיד? מלא את הטבלה.",
        "instruction_en": "What do you gain from this pattern? And what do you lose? Fill in the table.",
    },
    "S12": {
        "type": "tool",
        "tool_type": "trait_picker",
        "title_he": "כוחות מקור וטבע (כמ\"ז)",
        "title_en": "Source & Nature Forces (KMZ)",
        "instruction_he": "מהם הערכים והאמונות שמניעים אותך (מקור)? ומהן היכולות והכישרונות הטבעיים שלך (טבע)?",
        "instruction_en": "What are the values and beliefs that drive you (source)? And what are your natural abilities and talents (nature)?",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# STATE PERSISTENCE (Simple JSON in DB)
# ══════════════════════════════════════════════════════════════════════════════


def _get_conversation_or_404(
    conversation_id: int,
    user_id: int,
    db: Session,
) -> ConversationModel:
    """
    Load conversation and verify ownership.
    Raises HTTPException 404 if not found or not owned (avoids information disclosure).
    """
    conv = db.query(ConversationModel).filter(
        ConversationModel.id == conversation_id,
        ConversationModel.user_id == user_id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


def load_v2_state(conversation_id: int, db: Session) -> Dict[str, Any]:
    """
    Load V2 state from database.
    
    V2 state is stored in conversation.v2_state as JSON.
    """
    conv = db.query(ConversationModel).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Try to load state from v2_state
    if conv.v2_state and isinstance(conv.v2_state, dict):
        logger.info(f"[BSD V2 API] Loaded existing state with {len(conv.v2_state.get('messages', []))} messages")
        return conv.v2_state
    
    # Create new state if not found
    logger.info(f"[BSD V2 API] Creating new state for conversation {conversation_id}")
    return create_initial_state(
        conversation_id=str(conversation_id),
        user_id=str(conv.user_id),
        language="he"
    )


def save_v2_state(conversation_id: int, state: Dict[str, Any], db: Session) -> None:
    """
    Save V2 state to database.
    """
    conv = db.query(ConversationModel).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Save state to v2_state as JSON
    conv.v2_state = state
    
    # Update current_phase
    conv.current_phase = state.get("current_step", "S0")
    
    db.commit()
    logger.info(f"[BSD V2 API] Saved state with {len(state.get('messages', []))} messages")


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/warmup")
async def warmup_cache(
    current_user: User = Depends(get_current_user),
):
    """
    Pre-warm Azure prompt cache for new conversations.
    Call when user opens/creates a conversation - before first message.
    Returns immediately; warm-up runs in background.
    """
    import asyncio
    asyncio.create_task(warm_prompt_cache(language="he", steps=("S0", "S1")))
    return {"status": "warmup_started"}


@router.post("/message", response_model=ChatResponse)
@limiter.limit("30/minute")
async def send_message_v2(
    request: Request,
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_message_quota),
):
    """
    BSD V2 chat endpoint - single-agent conversational coach.
    
    Unlike V1's multi-layer architecture, V2 uses a single LLM call
    with rich context and clear guidance for natural conversation.
    
    Usage:
        POST /api/chat/v2/message
        {
            "message": "זוגיות",
            "conversation_id": 123,
            "language": "he"
        }
    
    Returns:
        {
            "coach_message": "זוגיות, אוקיי. ספר לי יותר...",
            "conversation_id": 123,
            "current_step": "S1",
            "saturation_score": 0.5
        }
    """
    state: Dict[str, Any] = {}
    safe_message: str | None = None
    try:
        safe_message = sanitize_chat_message(body.message)
        api_start = time.time()

        print(f"\n{'='*80}")
        print(f"[BSD V2 API] ✅ REQUEST RECEIVED")
        print(f"[BSD V2 API] User: {current_user.id}")
        print(f"[BSD V2 API] Conversation: {body.conversation_id}")
        print(f"[BSD V2 API] Message: {body.message[:50]}...")
        print(f"{'='*80}\n", flush=True)
        
        logger.info(f"[BSD V2 API] User {current_user.id} sent message to conv {body.conversation_id}")
        
        # Verify conversation ownership before any load/save
        _get_conversation_or_404(body.conversation_id, current_user.id, db)
        
        # Load state
        t1 = time.time()
        state = load_v2_state(body.conversation_id, db)
        t2 = time.time()
        logger.info(f"[PERF API] Load state from DB: {(t2-t1)*1000:.0f}ms")
        logger.info(f"[BSD V2 API] Loaded state: step={state['current_step']}, messages={len(state.get('messages', []))}")
        
        # Snapshot previous step BEFORE handle_conversation mutates state in-place.
        # This is required for reliable "stage entry" detection and tool activation.
        prev_step = state.get("current_step", "S0")

        # Handle conversation (pass user gender from dashboard for אתה/את)
        t3 = time.time()
        user_gender = getattr(current_user, "gender", None) or None
        coach_message, updated_state = await handle_conversation(
            user_message=safe_message,
            state=state,
            language=body.language,
            user_gender=user_gender,
            conversation_id=body.conversation_id,
        )
        t4 = time.time()
        logger.info(f"[PERF API] handle_conversation: {(t4-t3)*1000:.0f}ms")
        
        # Save state
        t5 = time.time()
        logger.info(f"[BSD V2 API] Saving state: step={updated_state['current_step']}, messages={len(updated_state.get('messages', []))}")
        save_v2_state(body.conversation_id, updated_state, db)
        t6 = time.time()
        logger.info(f"[PERF API] Save state to DB: {(t6-t5)*1000:.0f}ms")
        logger.info(f"[BSD V2 API] State saved successfully")
        
        # Also save messages to DB (for compatibility with UI)
        t7 = time.time()
        from app.database import utc_now
        
        # Save user message
        user_msg = Message(
            conversation_id=body.conversation_id,
            role="user",
            content=safe_message,
            timestamp=utc_now()
        )
        db.add(user_msg)
        
        # Save coach message (meta.phase for smart scroll in frontend)
        coach_msg = Message(
            conversation_id=body.conversation_id,
            role="assistant",
            content=coach_message,
            timestamp=utc_now(),
            meta={"phase": updated_state["current_step"]}
        )
        db.add(coach_msg)
        
        db.commit()
        t8 = time.time()
        logger.info(f"[PERF API] Save messages to DB: {(t8-t7)*1000:.0f}ms")
        
        # Detect stage entry: if the coach just moved into a new stage, activate its tool
        new_step = updated_state.get("current_step", "S0")
        tool_call = None
        if new_step != prev_step and new_step in _STAGE_TOOL_TRIGGERS:
            tool_call = _STAGE_TOOL_TRIGGERS[new_step]
            logger.info(f"[BSD V2 API] Activating tool for stage {new_step}: {tool_call['tool_type']}")

        response = ChatResponse(
            coach_message=coach_message,
            conversation_id=body.conversation_id,
            current_step=updated_state["current_step"],
            saturation_score=updated_state["saturation_score"],
            tool_call=tool_call,
        )
        
        api_end = time.time()
        api_total_ms = (api_end - api_start) * 1000
        
        print(f"\n{'='*80}")
        print(f"[BSD V2 API] ✅ RETURNING RESPONSE")
        print(f"[BSD V2 API] Message length: {len(coach_message)} chars")
        print(f"[BSD V2 API] Message preview: {coach_message[:100]}...")
        print(f"[BSD V2 API] Step: {updated_state['current_step']}")
        print(f"[BSD V2 API] Saturation: {updated_state['saturation_score']:.2f}")
        print(f"[PERF API] 🏁 TOTAL API TIME: {api_total_ms:.0f}ms ({api_total_ms/1000:.1f}s)")
        print(f"{'='*80}\n", flush=True)
        
        logger.info(f"[BSD V2 API] Returning response: coach_message length={len(coach_message)}")
        logger.info(f"[PERF API] 🏁 TOTAL API TIME: {api_total_ms:.0f}ms ({api_total_ms/1000:.1f}s)")
        
        return response

    except HTTPException:
        # Re-raise HTTPException (404, 401, etc.) without wrapping in 500
        raise
    except ChatMessageRejected as e:
        raise HTTPException(
            status_code=400,
            detail={"error": e.reason, "message": "Invalid message content"},
        )
    except Exception as e:
        logger.error(f"[BSD V2 API] Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            from ..bsd_v2.error_buffer import capture_error
            capture_error("chat_v2_api", e, {"conv_id": body.conversation_id})
        except Exception:
            pass
        # Return fallback instead of 500 - user gets friendly message, not network error
        fallback_he = "הייתה לי בעיה טכנית. תוכל לחזור על זה?"
        fallback_en = "I had a technical issue. Could you try again?"
        fallback_msg = fallback_he if (body.language or "he") == "he" else fallback_en
        try:
            from app.database import utc_now
            fb_user_content = (
                safe_message
                if safe_message is not None
                else (body.message or "")[:MAX_CHAT_MESSAGE_CHARS]
            )
            user_msg = Message(
                conversation_id=body.conversation_id,
                role="user",
                content=fb_user_content,
                timestamp=utc_now(),
            )
            coach_msg = Message(conversation_id=body.conversation_id, role="assistant", content=fallback_msg, timestamp=utc_now(), meta={"phase": state.get("current_step", "S1")})
            db.add(user_msg)
            db.add(coach_msg)
            db.commit()
        except Exception as db_err:
            logger.warning(f"[BSD V2 API] Could not save fallback messages: {db_err}")
        return ChatResponse(
            coach_message=fallback_msg,
            conversation_id=body.conversation_id,
            current_step=state.get("current_step", "S1"),
            saturation_score=state.get("saturation_score", 0.3),
        )


# ══════════════════════════════════════════════════════════════════════════════
# DEBUG: Recent errors (in-memory, last 20)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/debug/errors")
async def get_recent_errors_debug(
    _admin: User = Depends(get_current_admin_user),
):
    """Return recent BSD V2 errors for debugging. Admin only."""
    try:
        from ..bsd_v2.error_buffer import get_recent_errors
        return {"errors": get_recent_errors(), "count": len(get_recent_errors())}
    except Exception as e:
        return {"errors": [], "count": 0, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# DEBUG: Export last conversation (for analyzing coach behavior)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/debug/last-conversation")
async def get_last_conversation_debug(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Return the user's most recent V2 conversation in full (messages + state).
    Admin-only export for coach behavior analysis.
    """
    conv = db.query(ConversationModel).filter(
        ConversationModel.user_id == current_user.id,
        ConversationModel.v2_state.isnot(None)
    ).order_by(ConversationModel.created_at.desc()).first()
    
    if not conv or not conv.v2_state:
        return {"message": "No V2 conversation found", "conversation_id": None}
    
    state = conv.v2_state
    messages = state.get("messages", [])
    
    # Build readable transcript
    transcript = []
    for m in messages:
        role = m.get("sender") or m.get("role", "?")
        content = (m.get("content") or "").strip()
        if content:
            transcript.append({"role": role, "content": content})
    
    return {
        "conversation_id": conv.id,
        "title": conv.title,
        "current_step": state.get("current_step"),
        "saturation_score": state.get("saturation_score"),
        "collected_data": state.get("collected_data"),
        "transcript": transcript,
        "message_count": len(messages),
    }


@router.get("/debug/conversation/{conversation_id}")
async def get_conversation_debug(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Export a specific conversation for debugging (same format as last-conversation). Admin only."""
    conv = _get_conversation_or_404(conversation_id, current_user.id, db)
    if not conv.v2_state:
        return {"message": "Not a V2 conversation (no v2_state)", "conversation_id": conversation_id}
    
    state = conv.v2_state
    messages = state.get("messages", [])
    transcript = []
    for m in messages:
        role = m.get("sender") or m.get("role", "?")
        content = (m.get("content") or "").strip()
        if content:
            transcript.append({"role": role, "content": content})
    
    return {
        "conversation_id": conv.id,
        "title": conv.title,
        "current_step": state.get("current_step"),
        "saturation_score": state.get("saturation_score"),
        "collected_data": state.get("collected_data"),
        "transcript": transcript,
        "message_count": len(messages),
    }


# ══════════════════════════════════════════════════════════════════════════════
# INSIGHTS ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/conversations/{conversation_id}/insights")
async def get_conversation_insights_v2(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get accumulated cognitive data (insights) for a V2 conversation.
    
    Returns structured data including:
    - Current stage
    - Collected data (from collected_data in state)
    - Saturation score
    - Message count
    
    Usage:
        GET /api/chat/v2/conversations/123/insights
    
    Returns:
        {
            "current_stage": "S3",
            "saturation_score": 0.75,
            "cognitive_data": {
                "topic": "...",
                "event": "...",
                "emotions": [...],
                ...
            },
            "metrics": {
                "message_count": 15,
                "turns_in_current_stage": 5
            }
        }
    """
    try:
        logger.info(f"[BSD V2 API] Getting insights for conversation {conversation_id}")
        
        # Verify conversation ownership
        conv = _get_conversation_or_404(conversation_id, current_user.id, db)
        
        # Load V2 state
        state = load_v2_state(conversation_id, db)
        
        # Extract insights from state
        current_stage = state.get("current_step", "S0")
        saturation_score = state.get("saturation_score", 0.0)
        collected_data = state.get("collected_data", {})
        messages = state.get("messages", [])
        
        # Count turns in current stage
        turns_in_current_stage = sum(
            1 for msg in messages 
            if msg.get("role") == "user" and msg.get("metadata", {}).get("step") == current_stage
        )
        
        return {
            "current_stage": current_stage,
            "saturation_score": saturation_score,
            "cognitive_data": collected_data,
            "metrics": {
                "message_count": len(messages),
                "turns_in_current_stage": turns_in_current_stage
            },
            "updated_at": (conv_updated := getattr(conv, 'updated_at', None) or conv.created_at) and conv_updated.isoformat() or None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[BSD V2 API] Error getting insights: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

