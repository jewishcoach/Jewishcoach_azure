"""
Every chat turn stores how long each part took (coach message meta "timing_ms" — milliseconds only), and the V3
onboarding's /warm opens the Azure connection without a model call.
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
import app.api.chat_v2 as chat_v2
from app.database import Base, get_db
from app.dependencies import get_current_user
from app.limiter import limiter
from app.main import app
from app.middleware.usage_limiter import require_message_quota
from app.models import Conversation, Message, User


def _client(monkeypatch):
    # one in-memory DB for every thread (the endpoint runs in the TestClient's thread)
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    tag = uuid.uuid4().hex[:8]
    user = User(clerk_id=f"timing_{tag}", email=f"timing_{tag}@test.com", created_at=datetime.now(timezone.utc))
    db.add(user); db.commit(); db.refresh(user)
    conv = Conversation(user_id=user.id, v2_state={})
    db.add(conv); db.commit(); db.refresh(conv)
    app.dependency_overrides[get_current_user] = lambda: db.get(User, user.id)
    app.dependency_overrides[get_db] = lambda: db

    async def no_quota():
        return None

    app.dependency_overrides[require_message_quota] = no_quota
    monkeypatch.setattr(limiter, "enabled", False)
    return TestClient(app), db, conv


def test_turn_stores_timing_in_coach_meta(monkeypatch):
    async def fake_turn(user_message, state, **kwargs):
        state["_llm_ms"] = 1234
        state.setdefault("messages", []).append({"sender": "user", "content": user_message})
        state["messages"].append({"sender": "coach", "content": "ספר לי על רגע אחד"})
        return "ספר לי על רגע אחד", state

    monkeypatch.setattr(chat_v2, "handle_conversation", fake_turn)
    client, db, conv = _client(monkeypatch)
    try:
        res = client.post("/api/chat/v2/message", headers={"X-UX-Version": "3"},
                          json={"message": "אני מרגיש תקוע. בתחום: זוגיות", "conversation_id": conv.id, "language": "he"})
        assert res.status_code == 200, res.text
        coach = db.query(Message).filter_by(conversation_id=conv.id, role="assistant").one()
        timing = coach.meta["timing_ms"]
        assert timing["llm"] == 1234
        assert {"pre", "load", "coach", "post", "total"} <= set(timing)
        assert all(isinstance(v, int) and v >= 0 for v in timing.values())
        # the marker never reaches the saved state
        db.refresh(conv)
        assert "_llm_ms" not in (conv.v2_state or {})
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_warm_opens_the_azure_connection_without_a_model_call(monkeypatch):
    calls = []

    class FakeModels:
        async def list(self):
            calls.append("models.list")

    class FakeRoot:
        models = FakeModels()

    class FakeLLM:
        root_async_client = FakeRoot()

        async def ainvoke(self, *a, **k):  # pragma: no cover — must not be called
            raise AssertionError("warm must not call the model")

    monkeypatch.setattr(chat_v2, "get_azure_chat_llm_4o_mini", lambda: FakeLLM())
    client, db, _ = _client(monkeypatch)
    try:
        res = client.post("/api/chat/v2/warm")
        assert res.status_code == 200 and res.json() == {"ok": True}
        assert calls == ["models.list"]
    finally:
        app.dependency_overrides.clear()
        db.close()
