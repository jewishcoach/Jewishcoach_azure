"""
Admin API Endpoints

Protected endpoints for admin users to view quality flags,
system stats, and manage the LLM-as-a-Judge audit results.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..dependencies import get_current_admin_user
from ..database import get_db
from ..models import ConversationFlag, User, Conversation, Message
from typing import Optional

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)]  # ALL routes require admin
)

@router.get("/flags")
async def get_all_flags(
    db: Session = Depends(get_db),
    resolved: Optional[bool] = None,
    severity: Optional[str] = None,
    issue_type: Optional[str] = None
):
    """
    List all quality flags with filters.
    
    Query params:
    - resolved: Filter by resolution status (true/false)
    - severity: Filter by severity ("High", "Medium", "Low")
    - issue_type: Filter by issue type ("Hallucination", "Advice", "Logic Error", "Methodology")
    """
    query = db.query(ConversationFlag)
    
    if resolved is not None:
        query = query.filter(ConversationFlag.is_resolved == resolved)
    if severity:
        query = query.filter(ConversationFlag.severity == severity)
    if issue_type:
        query = query.filter(ConversationFlag.issue_type == issue_type)
    
    flags = query.order_by(ConversationFlag.created_at.desc()).all()
    
    # Enrich flags with conversation and message details
    enriched_flags = []
    for flag in flags:
        conversation = db.query(Conversation).filter(Conversation.id == flag.conversation_id).first()
        message = db.query(Message).filter(Message.id == flag.message_id).first()
        
        enriched_flags.append({
            "id": flag.id,
            "conversation_id": flag.conversation_id,
            "conversation_title": conversation.title if conversation else "Unknown",
            "message_id": flag.message_id,
            "message_content": message.content[:100] + "..." if message and len(message.content) > 100 else message.content if message else "",
            "stage": flag.stage,
            "issue_type": flag.issue_type,
            "reasoning": flag.reasoning,
            "severity": flag.severity,
            "is_resolved": flag.is_resolved,
            "created_at": flag.created_at.isoformat()
        })
    
    return {"flags": enriched_flags, "total": len(enriched_flags)}

@router.get("/stats")
async def get_system_stats(db: Session = Depends(get_db)):
    """
    Get system-wide quality metrics.
    
    Returns:
    - Total flags count
    - Unresolved flags count
    - Breakdown by severity
    - Breakdown by issue type
    - Breakdown by stage
    """
    total_flags = db.query(ConversationFlag).count()
    unresolved = db.query(ConversationFlag).filter(ConversationFlag.is_resolved == False).count()
    
    by_severity = {
        "High": db.query(ConversationFlag).filter(ConversationFlag.severity == "High").count(),
        "Medium": db.query(ConversationFlag).filter(ConversationFlag.severity == "Medium").count(),
        "Low": db.query(ConversationFlag).filter(ConversationFlag.severity == "Low").count()
    }
    
    by_issue_type = {
        "Hallucination": db.query(ConversationFlag).filter(ConversationFlag.issue_type == "Hallucination").count(),
        "Advice": db.query(ConversationFlag).filter(ConversationFlag.issue_type == "Advice").count(),
        "Logic Error": db.query(ConversationFlag).filter(ConversationFlag.issue_type == "Logic Error").count(),
        "Methodology": db.query(ConversationFlag).filter(ConversationFlag.issue_type == "Methodology").count()
    }
    
    # Get stage breakdown
    stage_counts = {}
    all_flags = db.query(ConversationFlag).all()
    for flag in all_flags:
        stage_counts[flag.stage] = stage_counts.get(flag.stage, 0) + 1
    
    return {
        "total_flags": total_flags,
        "unresolved_flags": unresolved,
        "by_severity": by_severity,
        "by_issue_type": by_issue_type,
        "by_stage": stage_counts,
        "resolution_rate": round((total_flags - unresolved) / total_flags * 100, 1) if total_flags > 0 else 0
    }

@router.patch("/flags/{flag_id}/resolve")
async def resolve_flag(
    flag_id: int,
    db: Session = Depends(get_db)
):
    """
    Mark a flag as resolved.
    
    This indicates the admin has reviewed the issue and taken action
    (e.g., improved prompts, updated methodology documentation).
    """
    flag = db.query(ConversationFlag).filter(ConversationFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    
    flag.is_resolved = True
    db.commit()
    return {"message": "Flag resolved", "flag_id": flag_id}

@router.get("/flags/{flag_id}")
async def get_flag_details(
    flag_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific flag,
    including the full conversation context.
    """
    flag = db.query(ConversationFlag).filter(ConversationFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    
    conversation = db.query(Conversation).filter(Conversation.id == flag.conversation_id).first()
    message = db.query(Message).filter(Message.id == flag.message_id).first()
    
    # Get surrounding messages for context (2 before, 2 after)
    all_messages = db.query(Message).filter(
        Message.conversation_id == flag.conversation_id
    ).order_by(Message.timestamp).all()
    
    # Find index of flagged message
    flagged_index = next((i for i, m in enumerate(all_messages) if m.id == flag.message_id), None)
    
    context_messages = []
    if flagged_index is not None:
        start = max(0, flagged_index - 2)
        end = min(len(all_messages), flagged_index + 3)
        context_messages = [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "is_flagged": m.id == flag.message_id
            }
            for m in all_messages[start:end]
        ]
    
    return {
        "id": flag.id,
        "conversation_id": flag.conversation_id,
        "conversation_title": conversation.title if conversation else "Unknown",
        "message_id": flag.message_id,
        "stage": flag.stage,
        "issue_type": flag.issue_type,
        "reasoning": flag.reasoning,
        "severity": flag.severity,
        "is_resolved": flag.is_resolved,
        "created_at": flag.created_at.isoformat(),
        "context_messages": context_messages
    }




