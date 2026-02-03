"""
Pydantic schemas.

This package is the single import target for `from app.schemas import ...`.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class MessageCreate(BaseModel):
    content: str
    language: Optional[str] = "he"  # Default to Hebrew


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    timestamp: datetime
    meta: dict = {}

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"


class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    current_phase: str = "S0"
    phase_history: list = []
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class JournalEntryCreate(BaseModel):
    content: str


class JournalEntryResponse(BaseModel):
    id: int
    user_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


