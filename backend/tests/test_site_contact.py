"""The school-site contact form is emailed to the office (Nov 10) — it used to be a mailto: link that sent nothing."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.routers.site_contact as site_contact
from app.main import app

FORM = {"name": "דנה כהן", "phone": "050-1234567", "email": "dana@example.com",
        "topic": "התאמת מאמן אישי (אחד על אחד)", "message": "שלום, <b>אשמח</b> לפרטים", "page": "/contact"}


def _capture(monkeypatch, ok=True):
    sent = []
    def fake(to, subject, body_html, body_plain=None, *, reply_to=None):
        sent.append({"to": to, "subject": subject, "html": body_html, "plain": body_plain, "reply_to": reply_to})
        return (ok, None if ok else "HttpResponseError: x")
    monkeypatch.setattr(site_contact, "send_html_email_detailed", fake)
    return sent


def test_form_is_emailed_to_the_office(monkeypatch):
    sent = _capture(monkeypatch)
    r = TestClient(app).post("/api/public/site-contact", json=FORM, headers={"X-Forwarded-For": "10.9.0.1"})
    assert r.status_code == 200, r.text
    assert len(sent) == 1
    m = sent[0]
    assert m["to"] == "office@bsdcoach.com" and m["reply_to"] == "dana@example.com"
    assert "דנה כהן" in m["subject"] and "050-1234567" in m["plain"]
    assert "<b>אשמח</b>" not in m["html"] and "&lt;b&gt;" in m["html"]  # the visitor's text is escaped


def test_bot_honeypot_sends_nothing(monkeypatch):
    sent = _capture(monkeypatch)
    r = TestClient(app).post("/api/public/site-contact", json={**FORM, "website": "http://spam"},
                             headers={"X-Forwarded-For": "10.9.0.2"})
    assert r.status_code == 200 and sent == []


def test_send_failure_is_reported(monkeypatch):
    _capture(monkeypatch, ok=False)
    r = TestClient(app).post("/api/public/site-contact", json=FORM, headers={"X-Forwarded-For": "10.9.0.3"})
    assert r.status_code == 502


def test_bad_email_rejected(monkeypatch):
    sent = _capture(monkeypatch)
    r = TestClient(app).post("/api/public/site-contact", json={**FORM, "email": "nope"}, headers={"X-Forwarded-For": "10.9.0.4"})
    assert r.status_code == 422 and sent == []


def test_cors_allows_the_school_site():
    r = TestClient(app).options("/api/public/site-contact", headers={
        "Origin": "https://www.bsdcoaching.co.il", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    assert r.headers.get("access-control-allow-origin") == "https://www.bsdcoaching.co.il"


def test_hostinger_smtp_is_used_when_configured(monkeypatch):
    """Nov 11: Hostinger refuses the app's sender domain, so the office mailbox sends the form to itself."""
    monkeypatch.setenv("SITE_CONTACT_SMTP_USER", "office@bsdcoach.com")
    monkeypatch.setenv("SITE_CONTACT_SMTP_PASSWORD", "pw")
    acs = _capture(monkeypatch)
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=0, context=None): sent["host"] = host
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def login(self, u, p): sent["user"] = u
        def send_message(self, m): sent["msg"] = m

    import smtplib
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    r = TestClient(app).post("/api/public/site-contact", json=FORM, headers={"X-Forwarded-For": "10.9.0.5"})
    assert r.status_code == 200, r.text
    m = sent["msg"]
    assert sent["host"] == "smtp.hostinger.com" and sent["user"] == "office@bsdcoach.com"
    assert m["To"] == "office@bsdcoach.com" and m["Reply-To"] == "dana@example.com" and "office@bsdcoach.com" in m["From"]
    assert acs == []  # the app's email service was not needed
