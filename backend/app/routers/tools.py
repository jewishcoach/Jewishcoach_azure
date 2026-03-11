from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db, utc_now
from ..models import ToolResponse, Conversation, Message, User
from ..dependencies import get_current_user
from pydantic import BaseModel, ConfigDict
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
    
    model_config = ConfigDict(from_attributes=True)

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
        created_at=utc_now()
    )
    db.add(tool_response)
    
    # Create a summary message so the V1 messages table stays in sync
    summary = _generate_tool_summary(request.tool_type, request.data)
    if summary:
        system_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=summary,
            timestamp=utc_now(),
            meta={"tool_submission": True, "tool_type": request.tool_type}
        )
        db.add(system_message)

    # Also inject the summary into the V2 state so handle_conversation sees it
    if conversation.v2_state and isinstance(conversation.v2_state, dict):
        try:
            v2_state = dict(conversation.v2_state)

            # Persist structured data directly into collected_data for insights panel
            if request.tool_type == "profit_loss":
                cd = dict(v2_state.get("collected_data") or {})
                stance = dict(cd.get("stance") or {})
                gains = request.data.get("gains", [])
                losses = request.data.get("losses", [])
                if gains:
                    stance["gains"] = gains
                if losses:
                    stance["losses"] = losses
                cd["stance"] = stance
                v2_state["collected_data"] = cd

            elif request.tool_type == "trait_picker":
                cd = dict(v2_state.get("collected_data") or {})
                forces = dict(cd.get("forces") or {})
                source = request.data.get("source_forces") or request.data.get("source_traits") or []
                nature = request.data.get("nature_forces") or request.data.get("nature_traits") or []
                if source:
                    forces["source"] = source
                if nature:
                    forces["nature"] = nature
                cd["forces"] = forces
                v2_state["collected_data"] = cd

            # Inject summary as user message so the LLM gets context
            if summary:
                messages = list(v2_state.get("messages", []))
                messages.append({
                    "sender": "user",
                    "content": summary,
                    "timestamp": utc_now().isoformat(),
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
        # Support both old keys (source_traits/nature_traits) and new keys (source_forces/nature_forces)
        source = data.get("source_forces") or data.get("source_traits") or []
        nature = data.get("nature_forces") or data.get("nature_traits") or []
        
        summary = "💎 **כוחות מקור וטבע (כמ\"ז) - התשובות שלי:**\n\n"
        
        if source:
            summary += "**כוחות מקור (ערכים ואמונות):**\n"
            for trait in source:
                summary += f"- {trait}\n"
        
        if nature:
            summary += "\n**כוחות טבע (יכולות וכישרונות):**\n"
            for trait in nature:
                summary += f"- {trait}\n"
        
        return summary.strip()
    
    elif tool_type == "vision_board_input":
        vision = data.get("vision", "")
        summary = f"🔮 **החזון שלי:**\n\n{vision}"
        return summary.strip()
    
    # Default: just stringify the data
    return f"[הגשת כלי: {tool_type}]"




