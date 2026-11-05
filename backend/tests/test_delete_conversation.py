"""
Deleting a conversation (V3 menu, Nov 5) removes its messages and cards, and the personality analyses that read it
— the one written for that conversation and the overall one. Another user's conversation can't be deleted.
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.models  # noqa: F401
from app.database import Base, get_db
from app.dependencies import get_current_user
from app.main import app
from app.models import Conversation, Message, ToolResponse, User


def test_delete_removes_the_conversation_and_its_analyses():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    tag = uuid.uuid4().hex[:8]
    user = User(clerk_id=f"del_{tag}", email=f"del_{tag}@test.com", created_at=datetime.now(timezone.utc))
    other = User(clerk_id=f"oth_{tag}", email=f"oth_{tag}@test.com", created_at=datetime.now(timezone.utc))
    db.add_all([user, other]); db.commit()
    gone, kept = Conversation(user_id=user.id, v2_state={}), Conversation(user_id=user.id, v2_state={})
    foreign = Conversation(user_id=other.id, v2_state={})
    db.add_all([gone, kept, foreign]); db.commit()
    db.add_all([Message(conversation_id=gone.id, role="user", content="פרטי"),
                ToolResponse(conversation_id=gone.id, tool_type="event_form", data={"when": "אתמול"})])
    user.preferences = {"conversation_analyses": {str(gone.id): {"letter": "a"}, str(kept.id): {"letter": "b"}},
                        "last_analysis": {"letter": "all"}, "analysis_consent": {"granted": True}}
    db.commit()
    app.dependency_overrides[get_current_user] = lambda: db.get(User, user.id)
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        assert client.delete(f"/api/chat/conversations/{foreign.id}").status_code == 403
        assert client.delete(f"/api/chat/conversations/{gone.id}").status_code == 200
        assert db.get(Conversation, gone.id) is None
        assert db.query(Message).filter_by(conversation_id=gone.id).count() == 0
        assert db.query(ToolResponse).filter_by(conversation_id=gone.id).count() == 0
        prefs = db.get(User, user.id).preferences
        assert list(prefs["conversation_analyses"]) == [str(kept.id)]
        assert "last_analysis" not in prefs and prefs["analysis_consent"] == {"granted": True}
        assert db.get(Conversation, foreign.id) is not None
    finally:
        app.dependency_overrides.clear()
        db.close()
