from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import JournalEntry, Conversation, User
from ..dependencies import get_current_user
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/journal", tags=["journal"])

class JournalSaveRequest(BaseModel):
    content: str

class JournalResponse(BaseModel):
    id: int
    conversation_id: int
    content: str
    updated_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/{conversation_id}", response_model=JournalResponse)
def get_journal(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get journal entry for a specific conversation"""
    # Verify conversation ownership
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=403, detail="Conversation not found or unauthorized")
    
    # Get or create journal entry
    journal = db.query(JournalEntry).filter(
        JournalEntry.conversation_id == conversation_id,
        JournalEntry.user_id == user.id
    ).first()
    
    if not journal:
        # Create empty journal entry
        journal = JournalEntry(
            user_id=user.id,
            conversation_id=conversation_id,
            content="",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(journal)
        db.commit()
        db.refresh(journal)
    
    return journal

@router.post("/{conversation_id}", response_model=JournalResponse)
def save_journal(
    conversation_id: int,
    request: JournalSaveRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save/update journal entry for a conversation (auto-save endpoint)"""
    # Verify conversation ownership
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=403, detail="Conversation not found or unauthorized")
    
    # Upsert journal entry
    journal = db.query(JournalEntry).filter(
        JournalEntry.conversation_id == conversation_id,
        JournalEntry.user_id == user.id
    ).first()
    
    if journal:
        # Update existing
        journal.content = request.content
        journal.updated_at = datetime.utcnow()
    else:
        # Create new
        journal = JournalEntry(
            user_id=user.id,
            conversation_id=conversation_id,
            content=request.content,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(journal)
    
    db.commit()
    db.refresh(journal)
    
    return journal




