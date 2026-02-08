"""
BSD V2 Chat API Endpoint

Side-by-side with V1 - experimental single-agent architecture.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..dependencies import get_current_user
from ..bsd_v2.single_agent_coach import handle_conversation
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
# ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

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
    try:
        print(f"\n{'='*80}")
        print(f"[BSD V2 API] ✅ REQUEST RECEIVED")
        print(f"[BSD V2 API] User: {current_user.id}")
        print(f"[BSD V2 API] Conversation: {request.conversation_id}")
        print(f"[BSD V2 API] Message: {request.message[:50]}...")
        print(f"{'='*80}\n", flush=True)
        
        logger.info(f"[BSD V2 API] User {current_user.id} sent message to conv {request.conversation_id}")
        
        # Load state
        state = load_v2_state(request.conversation_id, db)
        logger.info(f"[BSD V2 API] Loaded state: step={state['current_step']}, messages={len(state.get('messages', []))}")
        
        # Handle conversation
        coach_message, updated_state = await handle_conversation(
            user_message=request.message,
            state=state,
            language=request.language
        )
        
        # Save state
        logger.info(f"[BSD V2 API] Saving state: step={updated_state['current_step']}, messages={len(updated_state.get('messages', []))}")
        save_v2_state(request.conversation_id, updated_state, db)
        logger.info(f"[BSD V2 API] State saved successfully")
        
        # Also save messages to DB (for compatibility with UI)
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
        
        response = ChatResponse(
            coach_message=coach_message,
            conversation_id=request.conversation_id,
            current_step=updated_state["current_step"],
            saturation_score=updated_state["saturation_score"]
        )
        
        print(f"\n{'='*80}")
        print(f"[BSD V2 API] ✅ RETURNING RESPONSE")
        print(f"[BSD V2 API] Message length: {len(coach_message)} chars")
        print(f"[BSD V2 API] Message preview: {coach_message[:100]}...")
        print(f"[BSD V2 API] Step: {updated_state['current_step']}")
        print(f"[BSD V2 API] Saturation: {updated_state['saturation_score']:.2f}")
        print(f"{'='*80}\n", flush=True)
        
        logger.info(f"[BSD V2 API] Returning response: coach_message length={len(coach_message)}")
        
        return response
        
    except Exception as e:
        logger.error(f"[BSD V2 API] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[BSD V2 API] Error getting insights: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
