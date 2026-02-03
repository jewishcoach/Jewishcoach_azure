"""
Calendar, Goals, and Reminders endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
from ics import Calendar as ICSCalendar, Event
import json

from ..database import get_db
from ..models import User, CoachingGoal, CoachingReminder, Conversation
from ..dependencies import get_current_user
from ..schemas.calendar import (
    GoalCreate, GoalUpdate, GoalResponse,
    ReminderCreate, ReminderUpdate, ReminderResponse,
    CalendarExportRequest
)
from ..services import google_calendar

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


# ============================================================================
# GOALS ENDPOINTS
# ============================================================================

@router.post("/goals", response_model=GoalResponse)
def create_goal(
    goal: GoalCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new coaching goal"""
    db_goal = CoachingGoal(
        user_id=user.id,
        goal_type=goal.goal_type,
        title=goal.title,
        description=goal.description,
        target_count=goal.target_count,
        start_date=goal.start_date,
        end_date=goal.end_date
    )
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    
    return _enrich_goal_response(db_goal, db)


@router.get("/goals", response_model=List[GoalResponse])
def get_goals(
    status: str = None,  # Filter by status
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all goals for the current user"""
    query = db.query(CoachingGoal).filter(CoachingGoal.user_id == user.id)
    
    if status:
        query = query.filter(CoachingGoal.status == status)
    
    goals = query.order_by(CoachingGoal.created_at.desc()).all()
    
    return [_enrich_goal_response(g, db) for g in goals]


@router.get("/goals/{goal_id}", response_model=GoalResponse)
def get_goal(
    goal_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific goal"""
    goal = db.query(CoachingGoal).filter(
        CoachingGoal.id == goal_id,
        CoachingGoal.user_id == user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    return _enrich_goal_response(goal, db)


@router.patch("/goals/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: int,
    goal_update: GoalUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a goal"""
    goal = db.query(CoachingGoal).filter(
        CoachingGoal.id == goal_id,
        CoachingGoal.user_id == user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    if goal_update.title is not None:
        goal.title = goal_update.title
    if goal_update.description is not None:
        goal.description = goal_update.description
    if goal_update.target_count is not None:
        goal.target_count = goal_update.target_count
    if goal_update.current_count is not None:
        goal.current_count = goal_update.current_count
    if goal_update.status is not None:
        goal.status = goal_update.status
    
    goal.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(goal)
    
    return _enrich_goal_response(goal, db)


@router.delete("/goals/{goal_id}")
def delete_goal(
    goal_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a goal"""
    goal = db.query(CoachingGoal).filter(
        CoachingGoal.id == goal_id,
        CoachingGoal.user_id == user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    db.delete(goal)
    db.commit()
    
    return {"status": "deleted", "id": goal_id}


# ============================================================================
# REMINDERS ENDPOINTS
# ============================================================================

@router.post("/reminders", response_model=ReminderResponse)
def create_reminder(
    reminder: ReminderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new reminder"""
    db_reminder = CoachingReminder(
        user_id=user.id,
        title=reminder.title,
        description=reminder.description,
        reminder_date=reminder.reminder_date,
        reminder_time=reminder.reminder_time,
        repeat_type=reminder.repeat_type,
        repeat_days=reminder.repeat_days
    )
    db.add(db_reminder)
    db.commit()
    db.refresh(db_reminder)
    
    return _enrich_reminder_response(db_reminder)


@router.get("/reminders", response_model=List[ReminderResponse])
def get_reminders(
    active_only: bool = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all reminders for the current user"""
    query = db.query(CoachingReminder).filter(CoachingReminder.user_id == user.id)
    
    if active_only:
        query = query.filter(CoachingReminder.is_active == True)
    
    reminders = query.order_by(CoachingReminder.reminder_date).all()
    
    return [_enrich_reminder_response(r) for r in reminders]


@router.get("/reminders/upcoming", response_model=List[ReminderResponse])
def get_upcoming_reminders(
    days: int = 7,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get upcoming reminders for the next N days"""
    now = datetime.utcnow()
    future = now + timedelta(days=days)
    
    reminders = db.query(CoachingReminder).filter(
        CoachingReminder.user_id == user.id,
        CoachingReminder.is_active == True,
        CoachingReminder.reminder_date >= now,
        CoachingReminder.reminder_date <= future
    ).order_by(CoachingReminder.reminder_date).all()
    
    return [_enrich_reminder_response(r) for r in reminders]


@router.patch("/reminders/{reminder_id}", response_model=ReminderResponse)
def update_reminder(
    reminder_id: int,
    reminder_update: ReminderUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a reminder"""
    reminder = db.query(CoachingReminder).filter(
        CoachingReminder.id == reminder_id,
        CoachingReminder.user_id == user.id
    ).first()
    
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    if reminder_update.title is not None:
        reminder.title = reminder_update.title
    if reminder_update.description is not None:
        reminder.description = reminder_update.description
    if reminder_update.reminder_date is not None:
        reminder.reminder_date = reminder_update.reminder_date
    if reminder_update.reminder_time is not None:
        reminder.reminder_time = reminder_update.reminder_time
    if reminder_update.repeat_type is not None:
        reminder.repeat_type = reminder_update.repeat_type
    if reminder_update.repeat_days is not None:
        reminder.repeat_days = reminder_update.repeat_days
    if reminder_update.is_active is not None:
        reminder.is_active = reminder_update.is_active
    
    db.commit()
    db.refresh(reminder)
    
    return _enrich_reminder_response(reminder)


@router.delete("/reminders/{reminder_id}")
def delete_reminder(
    reminder_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a reminder"""
    reminder = db.query(CoachingReminder).filter(
        CoachingReminder.id == reminder_id,
        CoachingReminder.user_id == user.id
    ).first()
    
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    db.delete(reminder)
    db.commit()
    
    return {"status": "deleted", "id": reminder_id}


# ============================================================================
# CALENDAR EXPORT
# ============================================================================

@router.post("/export")
def export_calendar(
    export_request: CalendarExportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export calendar as ICS file"""
    calendar = ICSCalendar()
    calendar.creator = "Jewish Coach AI - beni@jewishcoach.ai"
    
    # Add past coaching sessions
    if export_request.include_past_sessions:
        query = db.query(Conversation).filter(Conversation.user_id == user.id)
        
        if export_request.start_date:
            query = query.filter(Conversation.created_at >= export_request.start_date)
        if export_request.end_date:
            query = query.filter(Conversation.created_at <= export_request.end_date)
        
        conversations = query.all()
        
        for conv in conversations:
            event = Event()
            event.name = conv.title or "אימון עם בני"
            event.begin = conv.created_at
            # Estimate 30 min duration
            event.duration = timedelta(minutes=30)
            event.description = f"שיחת אימון • {len(conv.messages)} הודעות • שלב: {conv.current_phase}"
            event.categories = ["Coaching", "Personal Development"]
            calendar.events.add(event)
    
    # Add reminders
    if export_request.include_reminders:
        query = db.query(CoachingReminder).filter(
            CoachingReminder.user_id == user.id,
            CoachingReminder.is_active == True
        )
        
        if export_request.start_date:
            query = query.filter(CoachingReminder.reminder_date >= export_request.start_date)
        if export_request.end_date:
            query = query.filter(CoachingReminder.reminder_date <= export_request.end_date)
        
        reminders = query.all()
        
        for reminder in reminders:
            event = Event()
            event.name = reminder.title
            event.begin = reminder.reminder_date
            if reminder.reminder_time:
                # Parse time and add to date
                hour, minute = map(int, reminder.reminder_time.split(':'))
                event.begin = reminder.reminder_date.replace(hour=hour, minute=minute)
            event.duration = timedelta(hours=1)
            if reminder.description:
                event.description = reminder.description
            event.categories = ["Reminder", "Coaching"]
            calendar.events.add(event)
    
    # Generate ICS content
    ics_content = str(calendar)
    
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f"attachment; filename=coaching_calendar_{user.id}.ics"
        }
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _enrich_goal_response(goal: CoachingGoal, db: Session) -> GoalResponse:
    """Add computed fields to goal response"""
    response = GoalResponse.from_orm(goal)
    
    # Calculate progress percentage
    if goal.target_count and goal.target_count > 0:
        response.progress_percentage = (goal.current_count / goal.target_count) * 100
    
    # Calculate days remaining
    now = datetime.utcnow()
    if goal.end_date > now:
        response.days_remaining = (goal.end_date - now).days
    else:
        response.days_remaining = 0
    
    # Check if completed
    response.is_completed = (
        goal.status == "completed" or
        (goal.target_count and goal.current_count >= goal.target_count)
    )
    
    return response


def _enrich_reminder_response(reminder: CoachingReminder) -> ReminderResponse:
    """Add computed fields to reminder response"""
    response = ReminderResponse.from_orm(reminder)
    
    # Calculate next reminder date (for repeating reminders)
    if reminder.repeat_type != "once":
        now = datetime.utcnow()
        if reminder.reminder_date < now:
            if reminder.repeat_type == "daily":
                response.next_reminder_date = reminder.reminder_date + timedelta(days=1)
            elif reminder.repeat_type == "weekly":
                response.next_reminder_date = reminder.reminder_date + timedelta(weeks=1)
            elif reminder.repeat_type == "biweekly":
                response.next_reminder_date = reminder.reminder_date + timedelta(weeks=2)
            elif reminder.repeat_type == "monthly":
                response.next_reminder_date = reminder.reminder_date + timedelta(days=30)
        else:
            response.next_reminder_date = reminder.reminder_date
    else:
        response.next_reminder_date = reminder.reminder_date
    
    return response


# ============================================================================
# GOOGLE CALENDAR INTEGRATION
# ============================================================================

@router.get("/google/auth-url")
def get_google_auth_url(
    user: User = Depends(get_current_user)
):
    """Get Google OAuth URL for calendar authorization"""
    import os
    try:
        auth_url = google_calendar.create_oauth_url(user.id)
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create auth URL: {str(e)}")


@router.get("/google/callback")
async def google_calendar_callback(
    code: str = Query(...),
    state: str = Query(...),  # This is the user_id
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback"""
    import os
    try:
        # Exchange code for tokens
        tokens = google_calendar.exchange_code_for_tokens(code)
        
        # Get user from state
        user_id = int(state)
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Store tokens in database
        user.google_calendar_token = json.dumps(tokens)
        user.google_calendar_refresh_token = tokens.get("refresh_token")
        db.commit()
        
        # Redirect to frontend success page
        return RedirectResponse(url=f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/?google_calendar=connected")
        
    except Exception as e:
        print(f"Google Calendar callback error: {e}")
        return RedirectResponse(url=f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/?google_calendar=error")


@router.post("/google/sync")
async def sync_google_calendar(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync reminders and past sessions to Google Calendar"""
    if not user.google_calendar_token:
        raise HTTPException(status_code=400, detail="Google Calendar not connected")
    
    try:
        # Get reminders
        reminders = db.query(CoachingReminder).filter(
            CoachingReminder.user_id == user.id,
            CoachingReminder.is_active == True
        ).all()
        
        # Get past sessions
        sessions = db.query(Conversation).filter(
            Conversation.user_id == user.id
        ).all()
        
        # Sync to Google Calendar
        result = await google_calendar.sync_to_google_calendar(
            user.google_calendar_token,
            reminders,
            sessions
        )
        
        if result["status"] == "success":
            user.google_calendar_synced_at = datetime.utcnow()
            db.commit()
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.delete("/google/disconnect")
def disconnect_google_calendar(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect Google Calendar integration"""
    user.google_calendar_token = None
    user.google_calendar_refresh_token = None
    user.google_calendar_synced_at = None
    db.commit()
    
    return {"status": "disconnected"}


@router.get("/google/status")
def get_google_calendar_status(
    user: User = Depends(get_current_user)
):
    """Check if user has Google Calendar connected"""
    return {
        "connected": user.google_calendar_token is not None,
        "last_synced": user.google_calendar_synced_at.isoformat() if user.google_calendar_synced_at else None
    }

