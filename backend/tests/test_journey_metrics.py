"""
Admin journey dashboard: steps reached, where clients stopped, loops inside a step — and its own password.
"""

import sys
import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.models  # noqa: F401
from app.database import Base, get_db
from app.dependencies import get_current_user
from app.limiter import limiter
from app.main import app
from app.models import Conversation, Message, ToolResponse, User
from app.services.journey_metrics import compute_journey

NOW = datetime(2026, 11, 5, 12, 0, 0)


def _db():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _conv(db, user, step, turns, start, cards=()):
    """turns: [(from_step, phase)] — one client message + one coach message each, a minute apart."""
    c = Conversation(user_id=user.id, v2_state={"current_step": step, "ux_version": 3}, created_at=start)
    db.add(c); db.commit()
    t = start
    for frm, phase in turns:
        db.add(Message(conversation_id=c.id, role="user", content="פרטי", timestamp=t))
        db.add(Message(conversation_id=c.id, role="assistant", content="פרטי", timestamp=t + timedelta(seconds=5),
                       meta={"from": frm, "phase": phase, "timing_ms": {"total": 3000}}))
        t += timedelta(minutes=1)
    for tool in cards:
        db.add(ToolResponse(conversation_id=c.id, tool_type=tool, data={}))
    db.commit()
    return c


def test_funnel_stalls_and_loops():
    db = _db()
    tag = uuid.uuid4().hex[:6]
    a = User(clerk_id=f"a{tag}", email=f"a{tag}@t.com", created_at=NOW - timedelta(days=3))
    b = User(clerk_id=f"b{tag}", email=f"b{tag}@t.com", created_at=NOW - timedelta(days=1))
    db.add_all([a, b]); db.commit()
    # a: stuck in S2 for 12 turns, last seen 2 days ago → stalled at S2, a loop
    _conv(db, a, "S2", [("S0", "S2")] + [("S2", "S2")] * 12, NOW - timedelta(days=2))
    # b: went to S15 and submitted the request → completed
    _conv(db, b, "S15", [("S0", "S2"), ("S2", "S3"), ("S3", "S5"), ("S14", "S15")], NOW - timedelta(hours=3),
          cards=("event_form", "commitment_card"))
    # an empty conversation (onboarding left) is not counted
    db.add(Conversation(user_id=b.id, v2_state={}, created_at=NOW - timedelta(hours=1))); db.commit()

    j = compute_journey(db, days=30, now=NOW)
    o = j["overview"]
    assert (o["conversations"], o["completed"], o["stalled"]) == (2, 1, 1)
    steps = {s["step"]: s for s in j["steps"]}
    assert steps["S2"]["reached"] == 2 and steps["S15"]["reached"] == 1
    assert steps["S2"]["stalled_here"] == 1 and steps["S2"]["loops"] == 1
    assert steps["S2"]["latency_p50"] == 3.0
    stuck = next(c for c in j["conversations"] if c["status"] == "stalled")
    assert (stuck["most_turns_step"], stuck["most_turns"]) == ("S2", 12)
    assert {u["id"]: u["messages_used"] for u in j["users"]}[a.id] == 13
    db.close()


def test_dashboard_needs_admin_and_its_password(monkeypatch):
    db = _db()
    admin = User(clerk_id=f"adm{uuid.uuid4().hex[:6]}", email="adm@t.com", is_admin=True, created_at=NOW)
    db.add(admin); db.commit()
    app.dependency_overrides[get_current_user] = lambda: db.get(User, admin.id)
    app.dependency_overrides[get_db] = lambda: db
    monkeypatch.setattr(limiter, "enabled", False)
    try:
        client = TestClient(app)
        monkeypatch.delenv("ADMIN_DASHBOARD_PASSWORD", raising=False)
        assert client.get("/api/admin/journey").status_code == 503  # closed until a password is set
        monkeypatch.setenv("ADMIN_DASHBOARD_PASSWORD", "right-one")
        assert client.get("/api/admin/journey", headers={"X-Admin-Password": "wrong"}).status_code == 403
        r = client.get("/api/admin/journey", headers={"X-Admin-Password": "right-one"})
        assert r.status_code == 200 and "steps" in r.json()
        db.get(User, admin.id).is_admin = False; db.commit()
        assert client.get("/api/admin/journey", headers={"X-Admin-Password": "right-one"}).status_code == 403
    finally:
        app.dependency_overrides.clear()
        db.close()
