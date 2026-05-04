"""Authenticated dashboard → support inbox contact form."""

from __future__ import annotations

import html
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, resolve_email_from_db_and_clerk
from ..email_visibility import normalize_public_email
from ..models import SupportEmailLog, User
from ..services.email_service import send_html_email_detailed
from ..services.support_mail_repo import append_support_email_log, normalize_customer_email

DEFAULT_SUPPORT_INBOX = "support@jewishcoacher.com"

router = APIRouter(prefix="/api/support", tags=["support"])


class ContactSupportBody(BaseModel):
    subject: str = Field(..., min_length=1, max_length=500)
    message: str = Field(..., min_length=1, max_length=20000)
    reply_email: EmailStr | None = None

    @field_validator("reply_email", mode="before")
    @classmethod
    def empty_reply_to_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v


def _canonical_reply_from_override(raw: str) -> str:
    pub = normalize_public_email(raw.strip())
    if not pub:
        raise HTTPException(
            status_code=400,
            detail="Please provide a real email address (not a placeholder inbox).",
        )
    return normalize_customer_email(pub)


def _customer_email_candidates(user: User) -> list[str]:
    raw_list: list[str] = []
    resolved = resolve_email_from_db_and_clerk(user.clerk_id, user.email)
    if resolved and "@" in resolved:
        raw_list.append(normalize_customer_email(resolved))
    if user.email and "@" in user.email:
        raw_list.append(normalize_customer_email(user.email))
    seen: set[str] = set()
    out: list[str] = []
    for x in raw_list:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _resolve_customer_reply_email(user: User, body: ContactSupportBody) -> str:
    if body.reply_email:
        return _canonical_reply_from_override(str(body.reply_email))
    resolved = resolve_email_from_db_and_clerk(user.clerk_id, user.email)
    pub = normalize_public_email(resolved) if resolved else None
    if pub:
        return normalize_customer_email(pub)
    raise HTTPException(
        status_code=400,
        detail="No email on file. Please enter your email address in the form.",
    )


def _serialize_log_row(row: SupportEmailLog) -> dict:
    body = row.body or ""
    if len(body) > 12_000:
        body = body[:12_000] + "…"
    ts = row.created_at.isoformat() if row.created_at else None
    return {
        "id": row.id,
        "direction": row.direction,
        "channel": row.channel,
        "subject": row.subject,
        "body": body,
        "created_at": ts,
    }


@router.get("/thread")
def get_support_thread(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=150, ge=1, le=300),
):
    """
    Chronological inbound/outbound support messages for the signed-in user
    (matched by user_id and/or normalized customer email variants).
    Omits draft rows (AI drafts / internal).
    """
    candidates = _customer_email_candidates(user)
    conds = [SupportEmailLog.user_id == user.id]
    if candidates:
        conds.append(SupportEmailLog.customer_email.in_(candidates))

    rows = (
        db.query(SupportEmailLog)
        .filter(or_(*conds))
        .filter(SupportEmailLog.direction.in_(["inbound", "outbound"]))
        .order_by(SupportEmailLog.created_at.asc(), SupportEmailLog.id.asc())
        .limit(limit)
        .all()
    )
    return {"items": [_serialize_log_row(r) for r in rows]}


@router.post("/contact")
def post_support_contact(
    body: ContactSupportBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reply_norm = _resolve_customer_reply_email(user, body)
    inbox = os.getenv("SUPPORT_INBOUND_MAILBOX", DEFAULT_SUPPORT_INBOX).strip() or DEFAULT_SUPPORT_INBOX

    subj = f"[Jewish Coach app] {body.subject.strip()}"
    esc_sub = html.escape(body.subject.strip())
    esc_msg = html.escape(body.message.strip())

    html_body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; line-height:1.5;">
<p><strong>From user id:</strong> {user.id}</p>
<p><strong>Clerk id:</strong> {html.escape(user.clerk_id)}</p>
<p><strong>Reply-To:</strong> {html.escape(reply_norm)}</p>
<p><strong>Subject:</strong> {esc_sub}</p>
<hr/>
<pre style="white-space:pre-wrap;font-family:inherit;">{esc_msg}</pre>
</body></html>"""

    plain = (
        f"From user id: {user.id}\n"
        f"Clerk id: {user.clerk_id}\n"
        f"Reply-To: {reply_norm}\n"
        f"Subject: {body.subject.strip()}\n\n"
        f"{body.message.strip()}"
    )

    append_support_email_log(
        db,
        customer_email=reply_norm,
        direction="inbound",
        channel="user_dashboard",
        subject=subj,
        body=body.message.strip(),
        meta={
            "source": "dashboard_contact",
            "user_id": user.id,
            "support_inbox": inbox,
        },
    )

    ok, err = send_html_email_detailed(
        inbox,
        subj,
        html_body,
        plain,
        reply_to=reply_norm,
    )
    if not ok:
        raise HTTPException(status_code=503, detail=err or "Email delivery failed")

    return {"ok": True, "support_inbox": inbox}
