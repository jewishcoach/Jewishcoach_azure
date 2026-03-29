"""
Pydantic schemas.

This package is the single import target for `from app.schemas import ...`.
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional, List
from datetime import datetime

from ..security.chat_input import MAX_CHAT_MESSAGE_CHARS


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=MAX_CHAT_MESSAGE_CHARS)
    language: Optional[str] = "he"  # Default to Hebrew


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    timestamp: datetime
    meta: dict = {}

    model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"


class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    current_phase: str = "S0"
    phase_history: list = []
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ConversationListItemResponse(BaseModel):
    """Lightweight row for GET /conversations (no message bodies)."""

    id: int
    title: str
    created_at: datetime
    current_phase: str = "S0"
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class FeedbackCreate(BaseModel):
    message_id: int
    score: int  # 1 or -1
    comment: Optional[str] = None
    category: Optional[str] = None


class SpeechTokenResponse(BaseModel):
    token: str
    region: str


class UserCreate(BaseModel):
    email: EmailStr
    preferences: Optional[dict] = {}


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime
    preferences: dict = {}

    model_config = ConfigDict(from_attributes=True)


class JournalEntryCreate(BaseModel):
    content: str


class JournalEntryResponse(BaseModel):
    id: int
    user_id: int
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


