"""
Tests for conversation insights - HudPanel data flow.

Verifies:
1. _v2_collected_data_to_cognitive_data transforms V2 schema correctly
2. Topic inference from messages when collected_data is empty
3. get_conversation_insights_safe returns cognitive_data for V2 conversations
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Import the transformation function - we need to access it from the chat module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.routers.chat import (
    _v2_collected_data_to_cognitive_data,
    _infer_topic_from_messages,
)


class TestV2CollectedDataToCognitiveData:
    """Unit tests for the V2 -> CognitiveData transformation."""

    def test_topic_from_collected(self):
        """Topic from collected_data.topic."""
        collected = {"topic": "זוגיות"}
        out = _v2_collected_data_to_cognitive_data(collected)
        assert out["topic"] == "זוגיות"

    def test_topic_inferred_from_messages_when_empty(self):
        """Topic inferred from user messages when collected_data has no topic."""
        collected = {}
        messages = [
            {"sender": "coach", "content": "שלום, על מה תרצה להתאמן?"},
            {"sender": "user", "content": "על הזוגיות שלי"},
        ]
        out = _v2_collected_data_to_cognitive_data(collected, messages)
        assert out["topic"] == "על הזוגיות שלי"

    def test_topic_placeholder_ignored(self):
        """Placeholder [נושא] should not be used as topic."""
        collected = {"topic": "[נושא]"}
        out = _v2_collected_data_to_cognitive_data(collected)
        assert "topic" not in out or out.get("topic") != "[נושא]"

    def test_emotions_in_event_actual(self):
        """Emotions mapped to event_actual.emotions_list."""
        collected = {"emotions": ["כעס", "תסכול"]}
        out = _v2_collected_data_to_cognitive_data(collected)
        assert out["event_actual"]["emotions_list"] == ["כעס", "תסכול"]

    def test_thought_and_action_in_event_actual(self):
        """Thought and action_actual in event_actual."""
        collected = {
            "thought": "אני לא מספיק טוב",
            "action_actual": "התחבאתי בחדר",
        }
        out = _v2_collected_data_to_cognitive_data(collected)
        assert out["event_actual"]["thought_content"] == "אני לא מספיק טוב"
        assert out["event_actual"]["action_content"] == "התחבאתי בחדר"

    def test_gap_analysis(self):
        """Gap name and score in gap_analysis."""
        collected = {"gap_name": "בריחה", "gap_score": 7}
        out = _v2_collected_data_to_cognitive_data(collected)
        assert out["gap_analysis"]["name"] == "בריחה"
        assert out["gap_analysis"]["score"] == 7

    def test_pattern_id(self):
        """Pattern mapped to pattern_id."""
        collected = {"pattern": "הימנעות"}
        out = _v2_collected_data_to_cognitive_data(collected)
        assert out["pattern_id"]["name"] == "הימנעות"

    def test_full_s1_flow(self):
        """Full S1 flow: topic only."""
        collected = {"topic": "מנהיגות בעבודה"}
        out = _v2_collected_data_to_cognitive_data(collected)
        assert out["topic"] == "מנהיגות בעבודה"
        assert "event_actual" not in out or not out.get("event_actual")

    def test_full_s3_flow(self):
        """S3: topic + emotions."""
        collected = {
            "topic": "זוגיות",
            "emotions": ["כעס", "עלבון", "תסכול"],
        }
        out = _v2_collected_data_to_cognitive_data(collected)
        assert out["topic"] == "זוגיות"
        assert out["event_actual"]["emotions_list"] == ["כעס", "עלבון", "תסכול"]

    def test_empty_collected_returns_empty(self):
        """Empty collected returns minimal/empty output."""
        out = _v2_collected_data_to_cognitive_data({})
        assert out == {}

    def test_empty_collected_with_messages_infers_topic(self):
        """Empty collected but 2+ messages infers topic."""
        collected = {}
        messages = [
            {"sender": "user", "content": "שלום"},
            {"sender": "coach", "content": "על מה תרצה להתאמן?"},
            {"sender": "user", "content": "על הקשר עם האבא שלי"},
        ]
        out = _v2_collected_data_to_cognitive_data(collected, messages)
        assert out["topic"] == "על הקשר עם האבא שלי"


class TestInferTopicFromMessages:
    """Unit tests for topic inference."""

    def test_infers_from_first_user_message(self):
        """First valid user message becomes topic."""
        messages = [
            {"sender": "coach", "content": "שלום"},
            {"sender": "user", "content": "על הזוגיות"},
        ]
        assert _infer_topic_from_messages(messages) == "על הזוגיות"

    def test_skips_short_messages(self):
        """Messages shorter than 5 chars are skipped."""
        messages = [
            {"sender": "user", "content": "כן"},
        ]
        assert _infer_topic_from_messages(messages) == ""

    def test_uses_role_or_sender(self):
        """Accepts both 'sender' and 'role' keys."""
        messages = [
            {"role": "user", "content": "על הלחץ בעבודה"},
        ]
        assert _infer_topic_from_messages(messages) == "על הלחץ בעבודה"

    def test_empty_messages_returns_empty(self):
        """Empty messages returns empty string."""
        assert _infer_topic_from_messages([]) == ""


class TestInsightsEndpoint:
    """Integration tests for GET /api/chat/conversations/{id}/insights/safe."""

    def test_insights_returns_cognitive_data_for_v2(self):
        """Insights endpoint returns cognitive_data when v2_state has collected_data."""
        from datetime import datetime
        from app.database import get_db, Base, engine
        import app.models  # noqa: F401
        from app.dependencies import get_current_user
        from app.models import Conversation, User
        from app.main import app
        from sqlalchemy.orm import sessionmaker

        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        user = User(
            clerk_id="test_clerk_insights",
            email="insights_test@test.com",
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        conv = Conversation(
            user_id=user.id,
            title="Insights Test",
            v2_state={
                "current_step": "S1",
                "saturation_score": 0.5,
                "collected_data": {"topic": "זוגיות"},
                "messages": [],
            },
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        user_id = user.id  # capture before override

        def override_get_db():
            try:
                yield db
            finally:
                pass

        def override_get_current_user():
            # Return a simple object to avoid SQLAlchemy lazy-load on user.id
            u = MagicMock()
            u.id = user_id
            return u

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            client = TestClient(app)
            resp = client.get(f"/api/chat/conversations/{conv.id}/insights/safe")
            assert resp.status_code == 200
            data = resp.json()
            assert data["exists"] is True
            assert data["current_stage"] == "S1"
            assert "cognitive_data" in data
            assert data["cognitive_data"]["topic"] == "זוגיות"
        finally:
            app.dependency_overrides.clear()
            db.close()

    def test_insights_not_found_returns_exists_false(self):
        """Non-existent conversation returns exists: false, not 404."""
        from datetime import datetime
        from app.database import get_db, Base, engine
        import app.models  # noqa: F401
        from app.dependencies import get_current_user
        from app.models import User
        from app.main import app
        from sqlalchemy.orm import sessionmaker

        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        user = User(
            clerk_id="test_clerk_404",
            email="404_insights@test.com",
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id  # capture before override

        def override_get_db():
            try:
                yield db
            finally:
                pass

        def override_get_current_user():
            # Return a simple object to avoid SQLAlchemy lazy-load on user.id
            u = MagicMock()
            u.id = user_id
            return u

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            client = TestClient(app)
            resp = client.get("/api/chat/conversations/99999/insights/safe")
            assert resp.status_code == 200
            data = resp.json()
            assert data["exists"] is False
            assert data["cognitive_data"] == {}
        finally:
            app.dependency_overrides.clear()
            db.close()
