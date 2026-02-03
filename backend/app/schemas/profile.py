"""
Profile and Dashboard schemas
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProfileUpdate(BaseModel):
    """Request to update user profile"""
    display_name: Optional[str] = None
    gender: Optional[str] = None  # "male", "female", or null
    
    class Config:
        json_schema_extra = {
            "example": {
                "display_name": "דוד",
                "gender": "male"
            }
        }


class ProfileResponse(BaseModel):
    """User profile information"""
    id: int
    email: Optional[str]
    display_name: Optional[str]
    gender: Optional[str]
    is_admin: bool
    current_plan: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    """Dashboard statistics for user"""
    total_conversations: int
    total_messages: int
    current_phase: Optional[str]
    days_active: int
    messages_this_month: int
    longest_conversation_messages: int
    favorite_coaching_phase: Optional[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_conversations": 15,
                "total_messages": 143,
                "current_phase": "S8",
                "days_active": 32,
                "messages_this_month": 45,
                "longest_conversation_messages": 28,
                "favorite_coaching_phase": "Situation"
            }
        }


class DashboardResponse(BaseModel):
    """Complete dashboard data"""
    profile: ProfileResponse
    stats: DashboardStats
    recent_conversations: list
    
    class Config:
        from_attributes = True


