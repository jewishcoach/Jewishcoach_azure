"""
BSD V2 Chat API Endpoint

Side-by-side with V1 - experimental single-agent architecture.
"""

import json
import logging
import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..dependencies import get_current_user
from ..bsd_v2.single_agent_coach import handle_conversation, warm_prompt_cache
from ..bsd_v2.state_schema_v2 import create_initial_state
from ..database import get_db
from ..models import User, Conversation as ConversationModel, Message
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat/v2", tags=["BSD V2"])


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ══════════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str
    conversation_id: int
    language: str = "he"


class ChatResponse(BaseModel):
    coach_message: str
    conversation_id: int
    current_step: str
    saturation_score: float


# ══════════════════════════════════════════════════════════════════════════════
# STATE PERSISTENCE (Simple JSON in DB)
# ══════════════════════════════════════════════════════════════════════════════

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


# NOTE: /message/stream must be registered before /message (more specific path first)
@router.post("/message/stream")
async def chat_v2_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """BSD V2 Chat with Streaming Response (SSE)."""
    try:
        state = load_v2_state(request.conversation_id, db)
        from ..bsd_v2.single_agent_coach_streaming import handle_conversation_stream

        async def generate():
            try:
                final_state = None
                async for chunk in handle_conversation_stream(
                    user_message=request.message,
                    state=state,
                    language=request.language
                ):
                    if chunk.startswith("\n__STATE_UPDATE__:"):
                        state_json = chunk.replace("\n__STATE_UPDATE__:", "")
                        final_state = json.loads(state_json)
                        save_v2_state(request.conversation_id, final_state, db)
                        db.commit()
                        yield f"data: {json.dumps({'type': 'done', 'state': {'current_step': final_state.get('current_step', 'S1'), 'saturation_score': final_state.get('saturation_score', 0)}})}\n\n"
                    elif chunk.startswith("\n__ERROR__:"):
                        error_msg = chunk.replace("\n__ERROR__:", "")
                        yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'content', 'chunk': chunk})}\n\n"
            except Exception as e:
                logger.error(f"Error in stream generation: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
        )
    except Exception as e:
        logger.error(f"Error in streaming endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=ChatResponse)
async def send_message_v2(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    try:
        api_start = time.time()

        print(f"\n{'='*80}")
        print(f"[BSD V2 API] ✅ REQUEST RECEIVED")
        print(f"[BSD V2 API] User: {current_user.id}")
        print(f"[BSD V2 API] Conversation: {request.conversation_id}")
        print(f"[BSD V2 API] Message: {request.message[:50]}...")
        print(f"{'='*80}\n", flush=True)
        
        logger.info(f"[BSD V2 API] User {current_user.id} sent message to conv {request.conversation_id}")
        
        # Load state
        t1 = time.time()
        state = load_v2_state(request.conversation_id, db)
        t2 = time.time()
        logger.info(f"[PERF API] Load state from DB: {(t2-t1)*1000:.0f}ms")
        logger.info(f"[BSD V2 API] Loaded state: step={state['current_step']}, messages={len(state.get('messages', []))}")
        
        # Handle conversation (pass user gender from dashboard for אתה/את)
        t3 = time.time()
        user_gender = getattr(current_user, "gender", None) or None
        coach_message, updated_state = await handle_conversation(
            user_message=request.message,
            state=state,
            language=request.language,
            user_gender=user_gender
        )
        t4 = time.time()
        logger.info(f"[PERF API] handle_conversation: {(t4-t3)*1000:.0f}ms")
        
        # Save state
        t5 = time.time()
        logger.info(f"[BSD V2 API] Saving state: step={updated_state['current_step']}, messages={len(updated_state.get('messages', []))}")
        save_v2_state(request.conversation_id, updated_state, db)
        t6 = time.time()
        logger.info(f"[PERF API] Save state to DB: {(t6-t5)*1000:.0f}ms")
        logger.info(f"[BSD V2 API] State saved successfully")
        
        # Also save messages to DB (for compatibility with UI)
        t7 = time.time()
        from datetime import datetime
        
        # Save user message
        user_msg = Message(
            conversation_id=request.conversation_id,
            role="user",
            content=request.message,
            timestamp=datetime.utcnow()
        )
        db.add(user_msg)
        
        # Save coach message
        coach_msg = Message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=coach_message,
            timestamp=datetime.utcnow()
        )
        db.add(coach_msg)
        
        db.commit()
        t8 = time.time()
        logger.info(f"[PERF API] Save messages to DB: {(t8-t7)*1000:.0f}ms")
        
        response = ChatResponse(
            coach_message=coach_message,
            conversation_id=request.conversation_id,
            current_step=updated_state["current_step"],
            saturation_score=updated_state["saturation_score"]
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
    except Exception as e:
        logger.error(f"[BSD V2 API] Error: {e}")
        import traceback
        traceback.print_exc()
        # Return fallback instead of 500 - user gets friendly message, not network error
        fallback_he = "הייתה לי בעיה טכנית. תוכל לחזור על זה?"
        fallback_en = "I had a technical issue. Could you try again?"
        fallback_msg = fallback_he if (request.language or "he") == "he" else fallback_en
        try:
            from datetime import datetime
            user_msg = Message(conversation_id=request.conversation_id, role="user", content=request.message, timestamp=datetime.utcnow())
            coach_msg = Message(conversation_id=request.conversation_id, role="assistant", content=fallback_msg, timestamp=datetime.utcnow())
            db.add(user_msg)
            db.add(coach_msg)
            db.commit()
        except Exception as db_err:
            logger.warning(f"[BSD V2 API] Could not save fallback messages: {db_err}")
        return ChatResponse(
            coach_message=fallback_msg,
            conversation_id=request.conversation_id,
            current_step=state.get("current_step", "S1"),
            saturation_score=state.get("saturation_score", 0.3),
        )


# ══════════════════════════════════════════════════════════════════════════════
# DEBUG: Export last conversation (for analyzing coach behavior)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/debug/last-conversation")
async def get_last_conversation_debug(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Return the user's most recent V2 conversation in full (messages + state).
    For debugging coach behavior - share output to analyze.
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
    current_user: User = Depends(get_current_user)
):
    """Export a specific conversation for debugging (same format as last-conversation)."""
    conv = db.query(ConversationModel).filter(
        ConversationModel.id == conversation_id,
        ConversationModel.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
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
        conv = db.query(ConversationModel).filter(
            ConversationModel.id == conversation_id,
            ConversationModel.user_id == current_user.id
        ).first()
        
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
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

