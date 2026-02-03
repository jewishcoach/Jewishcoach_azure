from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..models import User
from pydantic import BaseModel

router = APIRouter(prefix="/api/users", tags=["users"])

class UserPreferences(BaseModel):
    voice_gender: str = "female"  # 'male' or 'female'
    voice_language: str = "he"    # 'he' or 'en'

@router.get("/me")
def get_current_user_info(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's info"""
    return {
        "id": user.id,
        "clerk_id": user.clerk_id,
        "email": user.email,
        "display_name": user.display_name,
        "gender": user.gender,
        "isAdmin": user.is_admin,
        "created_at": user.created_at.isoformat()
    }

@router.get("/me/preferences")
def get_user_preferences(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's preferences"""
    return user.preferences or {"voice_gender": "female", "voice_language": "he"}

@router.patch("/me/preferences")
def update_user_preferences(
    prefs: UserPreferences,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the current user's preferences"""
    # Merge new preferences with existing ones
    current_prefs = user.preferences or {}
    updated_prefs = {**current_prefs, **prefs.dict()}
    user.preferences = updated_prefs
    db.commit()
    db.refresh(user)
    return user.preferences



