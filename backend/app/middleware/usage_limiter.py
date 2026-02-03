"""
Middleware for enforcing usage limits based on subscription plans
"""
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from ..models import User
from ..routers.billing import check_usage_limit, increment_usage


async def check_message_limit(request: Request, user: User, db: Session):
    """Check if user can send a message"""
    has_quota = check_usage_limit(db, user, "message")
    
    if not has_quota:
        raise HTTPException(
            status_code=429,  # Too Many Requests
            detail={
                "error": "quota_exceeded",
                "message": "You have reached your message limit for this billing period",
                "current_plan": user.current_plan,
                "upgrade_url": "/billing"
            }
        )
    
    # Increment usage
    increment_usage(db, user, "message", 1)


async def check_speech_limit(request: Request, user: User, db: Session, minutes: int = 1):
    """Check if user can use speech feature"""
    has_quota = check_usage_limit(db, user, "speech")
    
    if not has_quota:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "quota_exceeded",
                "message": "You have reached your speech minutes limit for this billing period",
                "current_plan": user.current_plan,
                "upgrade_url": "/billing"
            }
        )
    
    # Increment usage
    increment_usage(db, user, "speech", minutes)



