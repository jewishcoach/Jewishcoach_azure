import os

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user, admin_diagnosis_for_request
from ..models import User
from ..email_visibility import normalize_public_email

from pydantic import BaseModel

router = APIRouter(prefix="/api/users", tags=["users"])

class UserPreferences(BaseModel):
    voice_gender: str = "female"  # 'male' or 'female'
    voice_language: str = "he"    # 'he' or 'en'


class ClaimAdminBody(BaseModel):
    """One-time escape hatch when ADMIN_EMAIL / Clerk sync fails. Set ADMIN_PROMOTE_SECRET on the server."""

    secret: str


@router.get("/me")
def get_current_user_info(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's info"""
    return {
        "id": user.id,
        "clerk_id": user.clerk_id,
        "email": normalize_public_email(user.email),
        "display_name": user.display_name,
        "gender": user.gender,
        "isAdmin": user.is_admin,
        "created_at": user.created_at.isoformat()
    }


@router.get("/me/admin-diagnosis")
def admin_diagnosis(
    user: User = Depends(get_current_user),
    authorization: str | None = Header(None),
):
    """Authenticated self-diagnosis for missing admin button (no secrets returned)."""
    return admin_diagnosis_for_request(authorization, user)


@router.post("/me/claim-admin")
def claim_admin_role(
    body: ClaimAdminBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Promotes current user to admin when body.secret matches env ADMIN_PROMOTE_SECRET.
    Rotate/remove ADMIN_PROMOTE_SECRET after use.
    """
    expected = os.getenv("ADMIN_PROMOTE_SECRET", "").strip()
    if not expected or body.secret != expected:
        raise HTTPException(status_code=403, detail="Forbidden")
    user.is_admin = True
    db.commit()
    db.refresh(user)
    return {"ok": True, "isAdmin": True}


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



