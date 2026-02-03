"""
User profile and dashboard endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from collections import Counter

from ..database import get_db
from ..models import User, Conversation, Message
from ..dependencies import get_current_user
from ..schemas.profile import (
    ProfileUpdate,
    ProfileResponse,
    DashboardStats,
    DashboardResponse
)

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile"""
    return user


@router.patch("/me", response_model=ProfileResponse)
def update_my_profile(
    profile_update: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile"""
    
    # Update fields if provided
    if profile_update.display_name is not None:
        user.display_name = profile_update.display_name.strip() if profile_update.display_name else None
    
    if profile_update.gender is not None:
        # Validate gender
        if profile_update.gender not in ["male", "female", None, ""]:
            raise HTTPException(status_code=400, detail="Gender must be 'male', 'female', or null")
        user.gender = profile_update.gender if profile_update.gender else None
    
    db.commit()
    db.refresh(user)
    
    return user


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics for current user"""
    
    # Get all user's conversations
    conversations = db.query(Conversation).filter(
        Conversation.user_id == user.id
    ).all()
    
    total_conversations = len(conversations)
    
    # Get all messages
    total_messages = db.query(Message).join(Conversation).filter(
        Conversation.user_id == user.id
    ).count()
    
    # Current phase (from most recent conversation)
    current_phase = None
    if conversations:
        latest_conv = max(conversations, key=lambda c: c.created_at)
        current_phase = latest_conv.current_phase
    
    # Days active (since account creation)
    days_active = (datetime.utcnow() - user.created_at).days
    
    # Messages this month
    month_ago = datetime.utcnow() - timedelta(days=30)
    messages_this_month = db.query(Message).join(Conversation).filter(
        Conversation.user_id == user.id,
        Message.timestamp >= month_ago
    ).count()
    
    # Longest conversation
    longest_conversation_messages = 0
    for conv in conversations:
        msg_count = len(conv.messages)
        if msg_count > longest_conversation_messages:
            longest_conversation_messages = msg_count
    
    # Favorite coaching phase (most common phase across conversations)
    phases = [conv.current_phase for conv in conversations if conv.current_phase]
    favorite_phase = None
    if phases:
        phase_counter = Counter(phases)
        favorite_phase = phase_counter.most_common(1)[0][0]
    
    # Recent conversations (last 5)
    recent_conversations = sorted(
        conversations,
        key=lambda c: c.created_at,
        reverse=True
    )[:5]
    
    recent_conv_list = [
        {
            "id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at.isoformat(),
            "current_phase": conv.current_phase,
            "message_count": len(conv.messages)
        }
        for conv in recent_conversations
    ]
    
    stats = DashboardStats(
        total_conversations=total_conversations,
        total_messages=total_messages,
        current_phase=current_phase,
        days_active=days_active,
        messages_this_month=messages_this_month,
        longest_conversation_messages=longest_conversation_messages,
        favorite_coaching_phase=favorite_phase
    )
    
    return DashboardResponse(
        profile=ProfileResponse.from_orm(user),
        stats=stats,
        recent_conversations=recent_conv_list
    )



