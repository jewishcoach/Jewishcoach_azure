"""
The end-of-process gift (GET /profile/insights?conversation_id=…) reads only that conversation — it used to read all
of the user's conversations, keep the oldest 8000 chars, and return a cached analysis of an earlier conversation.
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.models  # noqa: F401
import app.bsd_v2.deep_analyzer as deep_analyzer
from app.database import Base, engine, get_db
from app.dependencies import get_current_user
from app.main import app
from app.models import Conversation, Message, User


def _setup():
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    tag = uuid.uuid4().hex[:8]
    user = User(clerk_id=f"gift_{tag}", email=f"gift_{tag}@test.com", created_at=datetime.now(timezone.utc),
                preferences={"analysis_consent": {"granted": True}})
    other = User(clerk_id=f"other_{tag}", email=f"other_{tag}@test.com", created_at=datetime.now(timezone.utc))
    db.add_all([user, other]); db.commit(); db.refresh(user); db.refresh(other)
    old = Conversation(user_id=user.id, v2_state={"collected_data": {"pattern": "ישן"}})
    cur = Conversation(user_id=user.id, v2_state={"collected_data": {"pattern": "נוכחי"}})
    foreign = Conversation(user_id=other.id, v2_state={})
    db.add_all([old, cur, foreign]); db.commit()
    for conv, word in ((old, "ישנה"), (cur, "נוכחית")):
        db.add(Message(conversation_id=conv.id, role="user", content=" ".join([word] * 200)))
    db.add(Message(conversation_id=cur.id, role="user", content="אני מוכן להתחיל"))
    db.commit()
    return db, user, old, cur, foreign


def test_gift_reads_only_the_current_conversation(monkeypatch):
    db, user, old, cur, foreign = _setup()
    seen = {}

    async def fake_analysis(conversations_data, single_conversation=False):
        seen["data"], seen["single"] = conversations_data, single_conversation
        return deep_analyzer.DeepViewLetter(generated_at="2026-10-29T00:00:00+00:00", conversations_analyzed=1,
                                            total_user_words=1, letter="x", closing_word="y")

    monkeypatch.setattr(deep_analyzer, "run_deep_analysis", fake_analysis)
    app.dependency_overrides[get_current_user] = lambda: db.get(User, user.id)
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        res = client.get(f"/api/profile/insights?conversation_id={cur.id}")
        assert res.status_code == 200, res.text
        assert seen["single"] is True and len(seen["data"]) == 1
        assert seen["data"][0]["collected_data"]["pattern"] == "נוכחי"
        assert all("ישנה" not in m and m != "אני מוכן להתחיל" for m in seen["data"][0]["user_messages"])
        # another user's conversation is not readable
        assert client.get(f"/api/profile/insights?conversation_id={foreign.id}").status_code == 404
    finally:
        app.dependency_overrides.clear()
        db.close()
