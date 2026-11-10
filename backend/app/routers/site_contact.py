"""
The contact form of the school site (bsdcoaching.co.il) — sent to the office by email (Nov 10).

The form used to open the visitor's mail app (mailto:). Nothing reached office@bsdcoach.com unless they pressed
"send" there, and visitors without a mail app got nothing although the site said "תודה!". Now the site posts
here and the server sends through the app's email service (ACS / SendGrid).

Not an open relay: the recipient is fixed (SITE_CONTACT_TO, default office@bsdcoach.com) and the visitor's address
is only the Reply-To. Rate-limited per IP; a hidden "website" field catches simple bots.
"""
import html
import logging
import os
import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..limiter import limiter
from ..services.email_service import send_html_email_detailed

router = APIRouter(prefix="/api/public", tags=["public"])
_log = logging.getLogger("app.site_contact")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _to_address() -> str:
    return os.getenv("SITE_CONTACT_TO", "office@bsdcoach.com").strip()


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
    ok, err = send_html_email_detailed(_to_address(), subject, html_body, plain, reply_to=email)
    if not ok:
        _log.error("site contact: email send failed (%s)", (err or "")[:80].split(":")[0])
        raise HTTPException(status_code=502, detail="send failed")
    _log.info("site contact: sent (topic=%s)", topic)
    return {"ok": True}
