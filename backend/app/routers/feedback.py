from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_admin_user, get_current_user
from ..limiter import limiter
from ..schemas import FeedbackCreate
from ..models import CoachFeedbackSurveySubmission, Conversation, Feedback, Message, User

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

_COACH_SURVEY_REQUIRED_CHOICE_KEYS = (
    "onboarding_welcome",
    "onboarding_intake",
    "stage_life_event",
    "stage_present_gap",
    "stage_pattern",
    "stage_paradigm",
    "stage_position",
    "stage_source_nature",
    "stage_new_position",
    "stage_new_paradigm_pattern",
    "stage_commitment",
    "coaching_spirit",
    "session_end_feeling",
    "recommend_trainees",
)


class CoachFeedbackSurveyCreate(BaseModel):
    respondent_name: str = Field(..., min_length=1, max_length=200)
    responses: dict[str, Any] = Field(default_factory=dict)

    @field_validator("respondent_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("respondent_name required")
        return s


def _message_belongs_to_user(db: Session, message_id: int, user_id: int) -> bool:
    """Verify message belongs to a conversation owned by the user."""
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        return False
    conv = db.query(Conversation).filter(
        Conversation.id == msg.conversation_id,
        Conversation.user_id == user_id,
    ).first()
    return conv is not None


def _validate_coach_survey_responses(responses: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in responses.items():
        if value is None:
            continue
        if isinstance(value, str):
            s = value.strip()
            if s:
                cleaned[key] = s[:8000]
        else:
            cleaned[key] = value

    for key, val in list(cleaned.items()):
        if key in _COACH_SURVEY_REQUIRED_CHOICE_KEYS and val == "other":
            if not str(cleaned.get(f"{key}_other", "")).strip():
                raise HTTPException(status_code=422, detail=f"Please specify 'other' for: {key}")

    return cleaned


@router.post("/coach-survey/submit")
@limiter.limit("10/minute")
def submit_coach_feedback_survey(
    request: Request,
    body: CoachFeedbackSurveyCreate,
    db: Session = Depends(get_db),
):
    """Public coach feedback survey — no auth required."""
    _ = request
    responses = _validate_coach_survey_responses(body.responses)
    row = CoachFeedbackSurveySubmission(
        respondent_name=body.respondent_name,
        responses=responses,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id}


@router.get("/coach-survey/submissions")
def list_coach_feedback_surveys(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Admin-only list of coach feedback survey submissions."""
    q = (
        db.query(CoachFeedbackSurveySubmission)
        .order_by(CoachFeedbackSurveySubmission.created_at.desc())
    )
    total = q.count()
    rows = q.offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "respondent_name": r.respondent_name,
                "responses": r.responses,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.post("/")
def submit_feedback(
    feedback: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit feedback for a message (learning loop). Message must belong to user's conversation."""
    if not _message_belongs_to_user(db, feedback.message_id, current_user.id):
        raise HTTPException(status_code=403, detail="Message not found or access denied")
    db_feedback = Feedback(**feedback.dict())
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return {"status": "success", "feedback_id": db_feedback.id}


@router.get("/{feedback_id}")
def get_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get feedback by ID. Only if the feedback's message belongs to user's conversation."""
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    if not _message_belongs_to_user(db, feedback.message_id, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return feedback
