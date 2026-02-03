"""
Schemas for coaching calendar, goals, and reminders
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ============================================================================
# GOALS
# ============================================================================

class GoalCreate(BaseModel):
    """Request to create a new goal"""
    goal_type: str  # 'weekly', 'monthly', 'custom'
    title: str
    description: Optional[str] = None
    target_count: Optional[int] = None
    start_date: datetime
    end_date: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "goal_type": "weekly",
                "title": "3 אימונים בשבוע",
                "description": "להגיע ל-3 שיחות אימון מלאות",
                "target_count": 3,
                "start_date": "2026-01-20T00:00:00",
                "end_date": "2026-01-26T23:59:59"
            }
        }


class GoalUpdate(BaseModel):
    """Request to update a goal"""
    title: Optional[str] = None
    description: Optional[str] = None
    target_count: Optional[int] = None
    current_count: Optional[int] = None
    status: Optional[str] = None  # 'active', 'completed', 'cancelled'


class GoalResponse(BaseModel):
    """Goal information"""
    id: int
    user_id: int
    goal_type: str
    title: str
    description: Optional[str]
    target_count: Optional[int]
    current_count: int
    start_date: datetime
    end_date: datetime
    status: str
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    progress_percentage: Optional[float] = None
    days_remaining: Optional[int] = None
    is_completed: bool = False
    
    class Config:
        from_attributes = True


# ============================================================================
# REMINDERS
# ============================================================================

class ReminderCreate(BaseModel):
    """Request to create a new reminder"""
    title: str
    description: Optional[str] = None
    reminder_date: datetime
    reminder_time: Optional[str] = None  # HH:MM format
    repeat_type: str = "once"  # 'once', 'daily', 'weekly', 'biweekly', 'monthly'
    repeat_days: Optional[List[int]] = None  # [0-6] for weekly reminders
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "אימון שבועי",
                "description": "זמן לשיחת אימון",
                "reminder_date": "2026-01-22T00:00:00",
                "reminder_time": "19:00",
                "repeat_type": "weekly",
                "repeat_days": [1, 3]  # Monday and Wednesday
            }
        }


class ReminderUpdate(BaseModel):
    """Request to update a reminder"""
    title: Optional[str] = None
    description: Optional[str] = None
    reminder_date: Optional[datetime] = None
    reminder_time: Optional[str] = None
    repeat_type: Optional[str] = None
    repeat_days: Optional[List[int]] = None
    is_active: Optional[bool] = None


class ReminderResponse(BaseModel):
    """Reminder information"""
    id: int
    user_id: int
    title: str
    description: Optional[str]
    reminder_date: datetime
    reminder_time: Optional[str]
    repeat_type: str
    repeat_days: Optional[List[int]]
    is_active: bool
    last_sent: Optional[datetime]
    created_at: datetime
    
    # Computed fields
    next_reminder_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# CALENDAR EXPORT
# ============================================================================

class CalendarExportRequest(BaseModel):
    """Request to export calendar"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_past_sessions: bool = True
    include_reminders: bool = True



