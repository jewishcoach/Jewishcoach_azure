"""
Tests for Chat V2 conversation ownership verification.

Verifies that a user cannot send messages to another user's conversation.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db, Base, engine
import app.models  # noqa: F401
from app.dependencies import get_current_user
from app.models import Conversation, User
from app.main import app
from sqlalchemy.orm import sessionmaker


class TestChatV2Ownership:
    """Tests for _get_conversation_or_404 and ownership enforcement in send_message_v2."""

    def test_send_message_rejects_other_users_conversation(self):
        """
        User B cannot send a message to User A's conversation.
        Must return 404 (not 403) to avoid information disclosure.
        """
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        # User A - owns the conversation
        user_a = User(
            clerk_id="test_clerk_owner",
            email="owner@test.com",
            created_at=datetime.now(timezone.utc),
        )
        db.add(user_a)
        db.commit()
        db.refresh(user_a)

        # User B - will try to access A's conversation
        user_b = User(
            clerk_id="test_clerk_attacker",
            email="attacker@test.com",
            created_at=datetime.now(timezone.utc),
        )
        db.add(user_b)
        db.commit()
        db.refresh(user_b)

        # Conversation owned by User A
        conv = Conversation(
            user_id=user_a.id,
            title="Owner's Conversation",
            v2_state={
                "current_step": "S1",
                "saturation_score": 0.0,
                "collected_data": {},
                "messages": [],
            },
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

        user_b_id = user_b.id  # capture before override

        def override_get_db():
            try:
                yield db
            finally:
                pass

        def override_get_current_user():
            u = MagicMock()
            u.id = user_b_id  # Current user is B, trying to access A's conv
            return u

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            client = TestClient(app)
            resp = client.post(
                "/api/chat/v2/message",
                json={
                    "message": "ניסיון גישה",
                    "conversation_id": conv.id,
                    "language": "he",
                },
            )
            assert resp.status_code == 404
            data = resp.json()
            assert "detail" in data
            assert data["detail"] == "Conversation not found"
        finally:
            app.dependency_overrides.clear()
            db.close()

    def test_get_conversation_debug_rejects_other_users(self):
        """
        User B cannot access User A's conversation via debug endpoint.
        """
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        user_a = User(
            clerk_id="test_clerk_debug_owner",
            email="debug_owner@test.com",
            created_at=datetime.now(timezone.utc),
        )
        db.add(user_a)
        db.commit()
        db.refresh(user_a)

        user_b = User(
            clerk_id="test_clerk_debug_other",
            email="debug_other@test.com",
            created_at=datetime.now(timezone.utc),
        )
        db.add(user_b)
        db.commit()
        db.refresh(user_b)

        conv = Conversation(
            user_id=user_a.id,
            title="Owner's Conv",
            v2_state={"current_step": "S1", "messages": []},
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id

        def override_get_db():
            try:
                yield db
            finally:
                pass

        def override_get_current_user():
            u = MagicMock()
            u.id = user_b.id
            return u

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            client = TestClient(app)
            resp = client.get(f"/api/chat/v2/debug/conversation/{conv_id}")
            assert resp.status_code == 404
            assert resp.json().get("detail") == "Conversation not found"
        finally:
            app.dependency_overrides.clear()
            db.close()

    def test_get_insights_rejects_other_users(self):
        """
        User B cannot get insights for User A's conversation.
        """
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        user_a = User(
            clerk_id="test_clerk_insights_owner",
            email="insights_owner@test.com",
            created_at=datetime.now(timezone.utc),
        )
        db.add(user_a)
        db.commit()
        db.refresh(user_a)

        user_b = User(
            clerk_id="test_clerk_insights_other",
            email="insights_other@test.com",
            created_at=datetime.now(timezone.utc),
        )
        db.add(user_b)
        db.commit()
        db.refresh(user_b)

        conv = Conversation(
            user_id=user_a.id,
            title="Insights Conv",
            v2_state={"current_step": "S1", "collected_data": {}, "messages": []},
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id

        def override_get_db():
            try:
                yield db
            finally:
                pass

        def override_get_current_user():
            u = MagicMock()
            u.id = user_b.id
            return u

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            client = TestClient(app)
            resp = client.get(f"/api/chat/v2/conversations/{conv_id}/insights")
            assert resp.status_code == 404
            assert resp.json().get("detail") == "Conversation not found"
        finally:
            app.dependency_overrides.clear()
            db.close()
