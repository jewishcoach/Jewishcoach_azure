from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..schemas import FeedbackCreate
from ..models import Feedback, Message, Conversation
from ..models import User

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


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






