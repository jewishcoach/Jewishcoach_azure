from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
from typing import Optional

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    clerk_id = Column(String, unique=True, index=True, nullable=False)  # Clerk unique ID
    email = Column(String, unique=True, index=True, nullable=True)  # Make nullable
    is_admin = Column(Boolean, default=False, nullable=False)  # Admin privileges for RBAC
    created_at = Column(DateTime, default=datetime.utcnow)
    preferences = Column(JSON, default={})  # e.g., {"tone": "warm", "voice": "he-IL-HilaNeural"}
    
    # Profile Information
    display_name = Column(String, nullable=True)  # User's preferred name
    gender = Column(String, nullable=True)  # "male", "female", or null
    
    # Billing & Usage
    stripe_customer_id = Column(String, unique=True, nullable=True)  # Stripe customer ID
    current_plan = Column(String, default="basic", nullable=False)  # basic, premium, pro
    
    # Google Calendar Integration
    google_calendar_token = Column(Text, nullable=True)  # Encrypted OAuth token
    google_calendar_refresh_token = Column(Text, nullable=True)  # Refresh token
    google_calendar_synced_at = Column(DateTime, nullable=True)  # Last sync time
    
    conversations = relationship("Conversation", back_populates="user")
    journal_entries = relationship("JournalEntry", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")
    usage_records = relationship("UsageRecord", back_populates="user")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)
    current_phase = Column(String, default="S0")  # Coaching phase tracking (S0-S10)
    phase_history = Column(JSON, default=[])  # Track phase transitions
    v2_state = Column(JSON, default=None)  # V2: Full conversation state (replaces phase tracking)
    
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    journal_entries = relationship("JournalEntry", back_populates="conversation", cascade="all, delete-orphan")
    tool_responses = relationship("ToolResponse", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    meta = Column(JSON, default={})  # sources, tools_used, etc.
    
    conversation = relationship("Conversation", back_populates="messages")
    feedback = relationship("Feedback", back_populates="message", uselist=False)

class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    score = Column(Integer, nullable=False)  # 1 (positive) or -1 (negative)
    comment = Column(Text, nullable=True)
    category = Column(String, nullable=True)  # "accuracy", "tone", "relevance"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    message = relationship("Message", back_populates="feedback")

class JournalEntry(Base):
    __tablename__ = "journal_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="journal_entries")
    conversation = relationship("Conversation", back_populates="journal_entries")

class ToolResponse(Base):
    __tablename__ = "tool_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    tool_type = Column(String, nullable=False)  # "profit_loss", "trait_picker", etc.
    data = Column(JSON, nullable=False)  # Tool-specific data
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="tool_responses")

class ConversationFlag(Base):
    """Quality audit flags from LLM-as-a-Judge system"""
    __tablename__ = "conversation_flags"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    stage = Column(String, nullable=False)  # Stage when issue occurred
    issue_type = Column(String, nullable=False)  # "Hallucination", "Advice", "Logic Error"
    reasoning = Column(Text, nullable=False)  # Judge's explanation
    severity = Column(String, nullable=False)  # "High", "Medium", "Low"
    is_resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    conversation = relationship("Conversation", backref="flags")
    message = relationship("Message", backref="flags")

# ============================================================================
# BILLING & SUBSCRIPTION MODELS
# ============================================================================

class Subscription(Base):
    """User subscription details"""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan = Column(String, nullable=False)  # "basic", "premium", "pro"
    status = Column(String, nullable=False)  # "active", "canceled", "expired", "trial"
    stripe_subscription_id = Column(String, unique=True, nullable=True)
    stripe_price_id = Column(String, nullable=True)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Coupon relationship
    coupon_code = Column(String, nullable=True)  # If activated via coupon
    
    user = relationship("User", back_populates="subscriptions")

class UsageRecord(Base):
    """Track user usage for quota limits"""
    __tablename__ = "usage_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    period_start = Column(DateTime, nullable=False)  # Start of billing period
    period_end = Column(DateTime, nullable=False)  # End of billing period
    messages_used = Column(Integer, default=0, nullable=False)
    speech_minutes_used = Column(Integer, default=0, nullable=False)  # In minutes
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="usage_records")

class Coupon(Base):
    """Promotional coupons for free access"""
    __tablename__ = "coupons"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)  # e.g., "BSD100"
    plan_granted = Column(String, nullable=False)  # "premium" or "pro"
    duration_days = Column(Integer, nullable=True)  # null = lifetime, or number of days
    max_uses = Column(Integer, nullable=True)  # null = unlimited
    current_uses = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Coupon expiration
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Metadata
    description = Column(Text, nullable=True)  # e.g., "BSD special launch offer"

class CouponRedemption(Base):
    """Track who redeemed which coupons"""
    __tablename__ = "coupon_redemptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=False)
    redeemed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # When the coupon benefit expires
    is_active = Column(Boolean, default=True, nullable=False)
    
    user = relationship("User", backref="coupon_redemptions")
    coupon = relationship("Coupon", backref="redemptions")


# ============================================================================
# BSD CORE (LangGraph Orchestrator) - State + Audit
# ============================================================================

class BsdSessionState(Base):
    """
    Structured BSD session state for a conversation.

    This is the 'State Object' described in the BSD report: it stores structured
    cognitive data separately from raw chat text so the process can be enforced
    deterministically across long sessions.
    """
    __tablename__ = "bsd_session_states"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, unique=True, index=True)

    # Stage identifier: S0..S10
    current_stage = Column(String, default="S0", nullable=False)

    # Structured extracted data (JSON) - see backend/app/bsd/state_schema.py
    cognitive_data = Column(JSON, default=dict)

    # Process metrics (JSON): shehiya_depth_score, loop_count_in_stage, etc.
    metrics = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    conversation = relationship("Conversation", backref="bsd_state", uselist=False)


class BsdAuditLog(Base):
    """
    Audit log of Reasoner (Gatekeeper) decisions.

    Every step records: stage, decision, reasons, and any extracted fields used
    to justify transitions. This is used for tuning thresholds and debugging
    'too strict' vs 'too soft' behavior.
    """
    __tablename__ = "bsd_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)

    stage = Column(String, nullable=False)  # S0..S10 at time of decision
    decision = Column(String, nullable=False)  # advance|loop|override
    next_stage = Column(String, nullable=True)

    reasons = Column(JSON, default=list)  # list[str]
    extracted = Column(JSON, default=dict)  # structured extractions for this turn
    raw_user_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("Conversation", backref="bsd_audit_logs")


class CoachingGoal(Base):
    """
    User's coaching goals and targets
    """
    __tablename__ = "coaching_goals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    goal_type = Column(String, nullable=False)  # 'weekly', 'monthly', 'custom'
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    target_count = Column(Integer, nullable=True)  # e.g., "3 sessions per week"
    current_count = Column(Integer, default=0)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String, default="active")  # 'active', 'completed', 'cancelled'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", backref="coaching_goals")


class CoachingReminder(Base):
    """
    Reminders for future coaching sessions
    """
    __tablename__ = "coaching_reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    reminder_date = Column(DateTime, nullable=False, index=True)
    reminder_time = Column(String, nullable=True)  # HH:MM format
    repeat_type = Column(String, default="once")  # 'once', 'daily', 'weekly', 'biweekly', 'monthly'
    repeat_days = Column(JSON, nullable=True)  # JSON array of weekday numbers [0-6]
    is_active = Column(Boolean, default=True)
    last_sent = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", backref="coaching_reminders")

