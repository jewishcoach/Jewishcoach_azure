"""
The contact form of the school site (bsdcoaching.co.il) — sent to the office by email (Nov 10).

The form used to open the visitor's mail app (mailto:). Nothing reached office@bsdcoach.com unless they pressed
"send" there, and visitors without a mail app got nothing although the site said "תודה!". Now the site posts
here and the server sends it — through the office mailbox's own Hostinger SMTP when configured (Nov 11), else
through the app's email service (ACS / SendGrid).

Not an open relay: the recipient is fixed (SITE_CONTACT_TO, default office@bsdcoach.com) and the visitor's address
is only the Reply-To. Rate-limited per IP; a hidden "website" field catches simple bots.
"""
import html
import logging
import os
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..services.onboarding_email_runtime import unsubscribe_token_ok, unsubscribe_user

from ..limiter import limiter
from ..services.email_service import send_html_email_detailed

router = APIRouter(prefix="/api/public", tags=["public"])  # also: the email unsubscribe link
_log = logging.getLogger("app.site_contact")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _to_address() -> str:
    return os.getenv("SITE_CONTACT_TO", "office@bsdcoach.com").strip()


# Nov 11: Hostinger (office@bsdcoach.com) refuses mail from the app's sender domain jewishcoacher.com — it has no MX
# ("450 4.1.8 Sender address rejected: Domain not found"), so ACS retried 12 h and gave up. The form is sent by the
# office mailbox itself through Hostinger's SMTP (bsdcoach.com → bsdcoach.com), login kept in App Service settings.
def _smtp_configured() -> bool:
    return bool(os.getenv("SITE_CONTACT_SMTP_USER", "").strip() and os.getenv("SITE_CONTACT_SMTP_PASSWORD", ""))


def _send_via_hostinger_smtp(subject: str, html_body: str, plain: str, *, reply_to: str) -> tuple[bool, str | None]:
    import smtplib
    import ssl
    from email.message import EmailMessage
    from email.utils import formataddr, make_msgid

    user = os.getenv("SITE_CONTACT_SMTP_USER", "").strip()
    host = os.getenv("SITE_CONTACT_SMTP_HOST", "smtp.hostinger.com").strip()
    port = int(os.getenv("SITE_CONTACT_SMTP_PORT", "465"))
    m = EmailMessage()
    m["Subject"] = subject
    m["From"] = formataddr(("טופס האתר bsdcoaching.co.il", user))
    m["To"] = _to_address()
    m["Reply-To"] = reply_to
    m["Message-ID"] = make_msgid(domain=user.split("@")[-1])
    m.set_content(plain)
    m.add_alternative(html_body, subtype="html")
    try:
        with smtplib.SMTP_SSL(host, port, timeout=20, context=ssl.create_default_context()) as s:
            s.login(user, os.getenv("SITE_CONTACT_SMTP_PASSWORD", ""))
            s.send_message(m)
        return True, None
    except Exception as e:  # never log the login or the message
        return False, type(e).__name__


class SiteContactRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    phone: str = Field(..., min_length=1, max_length=40)
    email: str = Field(..., min_length=3, max_length=200)
    topic: str = Field("", max_length=120)
    certification: str = Field("", max_length=300)
    message: str = Field("", max_length=5000)
    page: str = Field("", max_length=300)
    website: str = Field("", max_length=200)  # honeypot: hidden in the form, people leave it empty


@router.post("/site-contact")
@limiter.limit("5/minute;30/day")
def site_contact(request: Request, body: SiteContactRequest):
    if body.website.strip():
        return {"ok": True}  # a bot filled the hidden field: answer as usual, send nothing
    email = body.email.strip()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="invalid email")

    topic = body.topic.strip() or "פנייה כללית"
    rows = [
        ("שם", body.name.strip()),
        ("טלפון", body.phone.strip()),
        ("אימייל", email),
        ("נושא", topic),
        ("מוסד הכשרה קודם / תעודה", body.certification.strip()),
        ("עמוד", body.page.strip()),
    ]
    rows = [(k, v) for k, v in rows if v]
    msg = body.message.strip()
    plain = "\n".join(f"{k}: {v}" for k, v in rows) + (f"\n\n{msg}" if msg else "")
    esc = html.escape
    html_body = (
        '<div dir="rtl" style="font-family:Arial,sans-serif;font-size:15px;color:#1f3444">'
        "<h2 style=\"margin:0 0 12px\">פנייה חדשה מהאתר bsdcoaching.co.il</h2>"
        "<table style=\"border-collapse:collapse\">"
        + "".join(f'<tr><td style="padding:4px 0 4px 16px;font-weight:bold">{esc(k)}</td><td>{esc(v)}</td></tr>' for k, v in rows)
        + "</table>"
        + (f'<p style="white-space:pre-wrap;margin-top:16px;padding:12px;background:#f6f4f0;border-radius:8px">{esc(msg)}</p>' if msg else "")
        + '<p style="color:#888;font-size:12px;margin-top:16px">אפשר להשיב ישירות למייל הזה — התשובה תגיע לפונה.</p>'
        "</div>"
    )
    subject = f"פנייה מהאתר — {topic} — {body.name.strip()}"[:200]
    ok, err = (False, None)
    if _smtp_configured():
        ok, err = _send_via_hostinger_smtp(subject, html_body, plain, reply_to=email)
    if not ok:  # no Hostinger login, or it failed: the app's email service (may be refused by Hostinger, see above)
        ok, err = send_html_email_detailed(_to_address(), subject, html_body, plain, reply_to=email)
    if not ok:
        _log.error("site contact: email send failed (%s)", (err or "")[:80].split(":")[0])
        raise HTTPException(status_code=502, detail="send failed")
    _log.info("site contact: sent (topic=%s)", topic)
    return {"ok": True}


_UNSUB_PAGE = """<!DOCTYPE html><html dir="rtl" lang="he"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>הסרה מרשימת התפוצה</title></head>
<body style="font-family:Heebo,Arial,sans-serif;background:#f6f4f0;color:#1f3444;display:flex;min-height:100vh;
align-items:center;justify-content:center;margin:0;padding:24px"><div style="background:#fff;border-radius:20px;
padding:32px;max-width:420px;text-align:center;box-shadow:0 8px 24px rgba(0,0,0,.08)"><h1 style="font-size:22px">{title}</h1>
<p style="font-size:16px;line-height:1.6">{text}</p><p style="color:#64748b;font-size:13px">צוות BSD אימון יהודי</p></div></body></html>"""


@router.get("/email-unsubscribe", response_class=HTMLResponse)
@limiter.limit("20/minute")
def email_unsubscribe(request: Request, u: int, t: str, db: Session = Depends(get_db)):
    """The link at the bottom of every series email: stops the series for this user (Nov 10)."""
    user = db.get(User, u) if unsubscribe_token_ok(u, t) else None
    if not user:
        return HTMLResponse(_UNSUB_PAGE.format(title="הקישור לא תקין",
                                               text="אפשר לכתוב לנו ונסיר אתכם ידנית: support@jewishcoacher.com"), status_code=400)
    unsubscribe_user(db, user)
    return HTMLResponse(_UNSUB_PAGE.format(title="הוסרתם מרשימת התפוצה",
                                           text="לא נשלח אליכם יותר מיילים מהסדרה. האימון והשיחות שלכם נשארים כמו שהם."))
