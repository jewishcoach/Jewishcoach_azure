"""Nov 15: the V3 onboarding opened a new conversation on every load (the admin had 7 empty ones, five within 4 s).
POST /conversations reuses the user's fresh empty conversation; one with messages is never reused."""
import sys
import uuid
from datetime import datetime, timedelta, timezone
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
from app.models import Conversation, Message, User


def _client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    tag = uuid.uuid4().hex[:8]
    user = User(clerk_id=f"c_{tag}", email=f"c_{tag}@test.com", created_at=datetime.now(timezone.utc))
    db.add(user); db.commit()
    app.dependency_overrides[get_current_user] = lambda: db.get(User, user.id)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app), db, user


def test_repeated_creates_reuse_the_empty_conversation():
    c, db, user = _client()
    try:
        ids = {c.post("/api/chat/conversations", json={"language": "he"}).json()["id"] for _ in range(5)}
        assert len(ids) == 1
        assert db.query(Conversation).filter_by(user_id=user.id).count() == 1
    finally:
        app.dependency_overrides.clear(); db.close()


def test_a_started_or_old_conversation_is_not_reused():
    c, db, user = _client()
    try:
        first = c.post("/api/chat/conversations", json={"language": "he"}).json()["id"]
        db.add(Message(conversation_id=first, role="user", content="שלום")); db.commit()
        second = c.post("/api/chat/conversations", json={"language": "he"}).json()["id"]
        assert second != first
        conv = db.get(Conversation, second); conv.created_at = datetime.now(timezone.utc) - timedelta(days=2); db.commit()
        third = c.post("/api/chat/conversations", json={"language": "he"}).json()["id"]
        assert third not in (first, second)
    finally:
        app.dependency_overrides.clear(); db.close()
