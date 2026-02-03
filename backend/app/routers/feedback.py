from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import FeedbackCreate
from ..models import Feedback

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

@router.post("/")
def submit_feedback(feedback: FeedbackCreate, db: Session = Depends(get_db)):
    """Submit feedback for a message (learning loop)"""
    db_feedback = Feedback(**feedback.dict())
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return {"status": "success", "feedback_id": db_feedback.id}

@router.get("/{feedback_id}")
def get_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """Get feedback by ID"""
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback






