"""Series emails (Nov 10): no "שלום שם," when there is no name, signed by the team, and an unsubscribe link that works."""
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
import app.services.onboarding_email_runtime as rt
from app.database import Base, get_db
from app.main import app
from app.models import OnboardingEmailSequence, OnboardingEmailStep, User, UserOnboardingEmailState


def _db(monkeypatch):
    monkeypatch.setenv("ONBOARDING_EMAIL_CRON_SECRET", "test-secret")
    monkeypatch.setattr(rt, "resolve_onboarding_send_email", lambda u: u.email)
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    tag = uuid.uuid4().hex[:8]
    user = User(clerk_id=f"u_{tag}", email=f"u_{tag}@test.com", created_at=datetime.now(timezone.utc))
    db.add(user); db.commit()
    seq = OnboardingEmailSequence(name="t", is_active=True, is_default=True); db.add(seq); db.commit()
    for i in range(2):
        db.add(OnboardingEmailStep(sequence_id=seq.id, sort_order=i, delay_after_previous_minutes=0,
                                   subject=f"נושא {i}", body_html="<p>שלום {{display_name}},</p><p>תוכן</p>"))
    db.add(UserOnboardingEmailState(user_id=user.id, sequence_id=seq.id, next_step_index=0,
                                    next_send_at=datetime.now(timezone.utc) - timedelta(minutes=1), completed=False))
    db.commit()
    return db, user, seq


def test_no_name_says_shalom_without_placeholder(monkeypatch):
    db, user, seq = _db(monkeypatch)
    step = db.query(OnboardingEmailStep).first()
    _subj, html_body, plain = rt.build_final_html(step, user)
    assert "שלום," in html_body and "שלום שם" not in html_body
    user.display_name = "דנה"
    _subj, html_body, plain = rt.build_final_html(step, user)
    assert "שלום דנה," in html_body
    assert "צוות BSD אימון יהודי" in html_body and "/api/public/email-unsubscribe?u=" in html_body
    assert "להסרה מרשימת התפוצה" in plain


def test_unsubscribe_link_stops_the_series(monkeypatch):
    db, user, seq = _db(monkeypatch)
    sent = []
    monkeypatch.setattr(rt, "send_html_email", lambda *a, **k: sent.append(a) or True)
    app.dependency_overrides[get_db] = lambda: db
    try:
        c = TestClient(app)
        assert c.get(f"/api/public/email-unsubscribe?u={user.id}&t=wrong", headers={"X-Forwarded-For": "10.8.0.1"}).status_code == 400
        r = c.get(f"/api/public/email-unsubscribe?u={user.id}&t={rt.unsubscribe_token(user.id)}", headers={"X-Forwarded-For": "10.8.0.1"})
        assert r.status_code == 200 and "הוסרתם" in r.text
        db.refresh(user)
        assert user.preferences.get("onboarding_emails_off") is True
        st = db.query(UserOnboardingEmailState).filter_by(user_id=user.id).one()
        st.completed = False; st.next_send_at = datetime.now(timezone.utc) - timedelta(minutes=1); db.commit()  # even if re-queued
        rt.process_due_onboarding_emails(db)
        assert sent == []
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_series_sends_when_subscribed(monkeypatch):
    db, user, seq = _db(monkeypatch)
    sent = []
    monkeypatch.setattr(rt, "send_html_email", lambda *a, **k: sent.append(a) or True)
    out = rt.process_due_onboarding_emails(db)
    assert out["sent"] == 1 and len(sent) == 1
