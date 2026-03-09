from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import ToolResponse, Conversation, Message, User
from ..dependencies import get_current_user
from pydantic import BaseModel
from typing import Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])

class ToolSubmitRequest(BaseModel):
    tool_type: str
    data: Dict[str, Any]

class ToolResponseModel(BaseModel):
    id: int
    conversation_id: int
    tool_type: str
    data: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.post("/{conversation_id}/submit", response_model=ToolResponseModel)
async def submit_tool_response(
    conversation_id: int,
    request: ToolSubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit tool response data (e.g., Profit & Loss table, Trait Picker results)
    Optionally sends a summary back to the chat
    """
    # Verify conversation ownership
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=403, detail="Conversation not found or unauthorized")
    
    # Save tool response
    tool_response = ToolResponse(
        conversation_id=conversation_id,
        tool_type=request.tool_type,
        data=request.data,
        created_at=datetime.utcnow()
    )
    db.add(tool_response)
    
    # Create a summary message so the V1 messages table stays in sync
    summary = _generate_tool_summary(request.tool_type, request.data)
    if summary:
        system_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=summary,
            timestamp=datetime.utcnow(),
            meta={"tool_submission": True, "tool_type": request.tool_type}
        )
        db.add(system_message)

    # Also inject the summary into the V2 state so handle_conversation sees it
    if summary and conversation.v2_state and isinstance(conversation.v2_state, dict):
        try:
            v2_state = dict(conversation.v2_state)
            messages = list(v2_state.get("messages", []))
            messages.append({
                "sender": "user",
                "content": summary,
                "timestamp": datetime.utcnow().isoformat(),
                "internal_state": None,
            })
            v2_state["messages"] = messages
            conversation.v2_state = v2_state
            logger.info(f"[Tools] Injected {request.tool_type} submission into V2 state for conv {conversation_id}")
        except Exception as e:
            logger.warning(f"[Tools] Could not inject tool submission into V2 state: {e}")

    db.commit()
    db.refresh(tool_response)
    
    return tool_response

@router.get("/{conversation_id}/history", response_model=List[ToolResponseModel])
def get_tool_history(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all tool responses for a conversation"""
    # Verify conversation ownership
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=403, detail="Conversation not found or unauthorized")
    
    tool_responses = db.query(ToolResponse).filter(
        ToolResponse.conversation_id == conversation_id
    ).order_by(ToolResponse.created_at.desc()).all()
    
    return tool_responses

def _generate_tool_summary(tool_type: str, data: Dict[str, Any]) -> str:
    """Generate a human-readable summary of tool submission"""
    if tool_type == "profit_loss":
        gains = data.get("gains", [])
        losses = data.get("losses", [])
        
        summary = "📊 **טבלת רווח והפסד - התשובות שלי:**\n\n"
        
        if gains:
            summary += "**מה אני מרוויח:**\n"
            for gain in gains:
                summary += f"- {gain}\n"
        
        if losses:
            summary += "\n**מה אני מפסיד:**\n"
            for loss in losses:
                summary += f"- {loss}\n"
        
        return summary.strip()
    
    elif tool_type == "trait_picker":
        selected_traits = data.get("traits", [])
        source_traits = data.get("source_traits", [])
        nature_traits = data.get("nature_traits", [])
        
        summary = "🎯 **בחירת תכונות - התשובות שלי:**\n\n"
        
        if source_traits:
            summary += "**תכונות מקור:**\n"
            for trait in source_traits:
                summary += f"- {trait}\n"
        
        if nature_traits:
            summary += "\n**תכונות טבע:**\n"
            for trait in nature_traits:
                summary += f"- {trait}\n"
        
        return summary.strip()
    
    elif tool_type == "vision_board_input":
        vision = data.get("vision", "")
        summary = f"🔮 **החזון שלי:**\n\n{vision}"
        return summary.strip()
    
    # Default: just stringify the data
    return f"[הגשת כלי: {tool_type}]"




