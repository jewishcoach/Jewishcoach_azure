"""
A successful PayMe payment adds 1,000 messages from the moment of payment (user's decision Nov 8): a basic user
out of messages pays (PayMe mocked — no money moves) and can send again; paying again adds another 1,000 on top of
what is left; the webhook for the same sale adds nothing; a declined card changes nothing.
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
import app.routers.billing as billing
from app.database import Base, get_db
from app.dependencies import get_current_user
from app.main import app
from app.models import Conversation, Message, PayMeCheckoutIntent, User


def _setup(monkeypatch, declined=False):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    tag = uuid.uuid4().hex[:8]
    user = User(clerk_id=f"pay_{tag}", email=f"pay_{tag}@test.com", current_plan="basic", created_at=datetime.now(timezone.utc))
    db.add(user); db.commit()
    conv = Conversation(user_id=user.id, v2_state={}); db.add(conv); db.commit()
    db.add_all([Message(conversation_id=conv.id, role="user", content="x") for _ in range(200)]); db.commit()
    monkeypatch.setattr(billing, "payme_webhook_secret", lambda: "")
    monkeypatch.setattr(billing, "payme_is_ready_for_requests", lambda: True)
    monkeypatch.setattr(billing, "payme_generate_sale",
                        lambda **kw: {"status_code": 1 if declined else 0, "payme_sale_id": "SALE123"})
    monkeypatch.setattr(billing, "payme_response_failed", lambda resp: declined)
    app.dependency_overrides[get_current_user] = lambda: db.get(User, user.id)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app), db, user


def _limit(client):
    return client.get("/api/billing/overview").json()["usage"]["messages_limit"]


def _pay(client):
    return client.post("/api/billing/payme/subscribe", json={"plan": "premium", "buyer_token": "tok_123456"})


def test_payment_adds_1000_messages_and_can_be_bought_again(monkeypatch):
    client, db, user = _setup(monkeypatch)
    try:
        u = db.get(User, user.id)
        assert billing.check_usage_limit(db, u, "message") is False  # out of messages before paying (200/200)
        r = _pay(client)
        assert r.status_code == 200, r.text
        u = db.get(User, user.id)
        assert u.current_plan == "premium"
        assert billing.check_usage_limit(db, u, "message") is True  # can send again
        assert _limit(client) == 1200  # 200 used + 1,000 bought

        # 500 of them used, then a second payment: the 500 left are kept and 1,000 more come on top
        conv = db.query(Conversation).filter(Conversation.user_id == user.id).first()
        db.add_all([Message(conversation_id=conv.id, role="user", content="y") for _ in range(500)]); db.commit()
        r = _pay(client)
        assert r.status_code == 200, r.text
        assert _limit(client) == 2200

        # the PayMe webhook for a sale that was already applied adds nothing
        tid = r.json()["transaction_id"]
        intent = db.query(PayMeCheckoutIntent).filter(PayMeCheckoutIntent.transaction_id == tid).one()
        intent.fulfilled_at = None; db.commit()  # even if the webhook slips past the fulfilled check
        billing._apply_payme_paid_plan(db, db.get(User, user.id), "premium", tid, None); db.commit()
        assert _limit(client) == 2200

        # once the bought messages are used up the user is stopped again, and the quota gate (429) applies to Premium
        db.add_all([Message(conversation_id=conv.id, role="user", content="z") for _ in range(1500)]); db.commit()
        assert billing.check_usage_limit(db, db.get(User, user.id), "message") is False
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_unlimited_account_is_not_charged(monkeypatch):
    client, db, user = _setup(monkeypatch)
    try:
        u = db.get(User, user.id); u.is_admin = True; db.commit()
        assert _pay(client).status_code == 400
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_declined_card_changes_nothing(monkeypatch):
    client, db, user = _setup(monkeypatch, declined=True)
    try:
        r = client.post("/api/billing/payme/subscribe", json={"plan": "premium", "buyer_token": "tok_123456"})
        assert r.status_code == 402
        u = db.get(User, user.id)
        assert u.current_plan == "basic" and billing.check_usage_limit(db, u, "message") is False
    finally:
        app.dependency_overrides.clear()
        db.close()
