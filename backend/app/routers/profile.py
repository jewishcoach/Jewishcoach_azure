"""
User profile and dashboard endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from collections import Counter
import json

from ..database import get_db
from ..models import User, Conversation, Message
from ..routers.billing import get_or_create_current_usage
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
    
    # Days with at least one conversation (distinct calendar days of conversation start).
    # Matches the coaching calendar, which marks days by conversation created_at.
    now_utc = datetime.now(timezone.utc)
    unique_conv_days = set()
    for conv in conversations:
        if conv.created_at is None:
            continue
        ca = conv.created_at
        if ca.tzinfo is None:
            ca = ca.replace(tzinfo=timezone.utc)
        else:
            ca = ca.astimezone(timezone.utc)
        unique_conv_days.add(ca.date())
    days_active = len(unique_conv_days)

    # User messages in current billing period (matches subscription / usage_records)
    usage = get_or_create_current_usage(db, user)
    messages_this_month = usage.messages_used
    
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
    
    def _conv_summary(conv: Conversation) -> dict:
        return {
            "id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at.isoformat(),
            "current_phase": conv.current_phase,
            "message_count": len(conv.messages),
        }

    recent_conv_list = [_conv_summary(conv) for conv in recent_conversations]
    calendar_conv_list = [
        _conv_summary(c)
        for c in sorted(conversations, key=lambda x: x.created_at, reverse=True)
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
        recent_conversations=recent_conv_list,
        calendar_conversations=calendar_conv_list,
    )


# ══════════════════════════════════════════════════════════════════════════════
# INSIGHTS — Deep psychological profile analysis
# ══════════════════════════════════════════════════════════════════════════════

MIN_USER_WORDS = 150   # minimum words across all conversations to unlock analysis
CACHE_TTL_DAYS = 7     # days before re-analysis is recommended


@router.post("/insights/consent")
def grant_insights_consent(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Store user's explicit consent to analyze their conversations."""
    prefs: dict = dict(user.preferences or {})
    prefs["analysis_consent"] = {
        "granted": True,
        "granted_at": datetime.now(timezone.utc).isoformat(),
    }
    user.preferences = prefs
    db.commit()
    return {"status": "consent_granted"}


@router.delete("/insights/consent")
def revoke_insights_consent(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke consent and wipe any cached analysis."""
    prefs: dict = dict(user.preferences or {})
    prefs["analysis_consent"] = {"granted": False}
    prefs.pop("last_analysis", None)
    user.preferences = prefs
    db.commit()
    return {"status": "consent_revoked"}


@router.get("/insights/status")
def get_insights_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return whether the user can request an analysis and if a cached one exists.
    Frontend uses this to decide which screen to show.
    """
    prefs: dict = user.preferences or {}
    consent = prefs.get("analysis_consent", {})
    has_consent = consent.get("granted", False)

    # Count user words across all conversations
    user_messages = (
        db.query(Message)
        .join(Conversation)
        .filter(
            Conversation.user_id == user.id,
            Message.role == "user",
        )
        .all()
    )
    total_words = sum(len(m.content.split()) for m in user_messages if m.content)
    n_conversations = (
        db.query(Conversation).filter(Conversation.user_id == user.id).count()
    )

    cached = prefs.get("last_analysis")
    cache_stale = False
    if cached:
        try:
            generated_at = datetime.fromisoformat(cached.get("generated_at", ""))
            age_days = (datetime.now(timezone.utc) - generated_at.replace(tzinfo=timezone.utc)).days
            cache_stale = age_days >= CACHE_TTL_DAYS
        except Exception:
            cache_stale = True

    return {
        "has_consent": has_consent,
        "total_user_words": total_words,
        "n_conversations": n_conversations,
        "unlocked": total_words >= MIN_USER_WORDS,
        "min_words_required": MIN_USER_WORDS,
        "has_cached_analysis": cached is not None,
        "cache_stale": cache_stale,
    }


@router.get("/insights")
async def get_profile_insights(
    refresh: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return deep psychological insights for the current user.

    - Returns cached analysis if fresh (< CACHE_TTL_DAYS old) and refresh=False.
    - Runs new LLM analysis otherwise.
    - Requires consent + MIN_USER_WORDS.
    """
    from ..bsd_v2.deep_analyzer import run_deep_analysis

    prefs: dict = dict(user.preferences or {})

    # Check consent
    consent = prefs.get("analysis_consent", {})
    if not consent.get("granted", False):
        raise HTTPException(status_code=403, detail="analysis_consent_required")

    # Collect conversations with sufficient content
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.asc())
        .all()
    )

    conversations_data = []
    total_words = 0
    for conv in conversations:
        user_msgs = [m.content for m in conv.messages if m.role == "user" and m.content]
        words = sum(len(t.split()) for t in user_msgs)
        total_words += words
        if words < 20:
            continue
        cd = {}
        if conv.v2_state:
            state = conv.v2_state if isinstance(conv.v2_state, dict) else {}
            cd = state.get("collected_data") or {}
        conversations_data.append({
            "collected_data": cd,
            "user_messages": user_msgs,
            "message_count": len(conv.messages),
        })

    if total_words < MIN_USER_WORDS:
        raise HTTPException(
            status_code=422,
            detail=f"insufficient_data: {total_words}/{MIN_USER_WORDS} words",
        )

    if not conversations_data:
        raise HTTPException(status_code=422, detail="no_qualifying_conversations")

    # Return cache if fresh and not forced refresh
    cached = prefs.get("last_analysis")
    if cached and not refresh:
        try:
            generated_at = datetime.fromisoformat(cached.get("generated_at", ""))
            age_days = (datetime.now(timezone.utc) - generated_at.replace(tzinfo=timezone.utc)).days
            if age_days < CACHE_TTL_DAYS:
                return cached
        except Exception:
            pass

    # Run analysis
    insights = await run_deep_analysis(conversations_data)
    result = insights.model_dump()

    # Cache in user preferences
    prefs["last_analysis"] = result
    user.preferences = prefs
    db.commit()

    return result
