"""Authenticated dashboard → support inbox contact form."""

from __future__ import annotations

import html
import json
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
from ..services.support_mail_repo import (
    append_support_email_log,
    normalize_customer_email,
    _candidate_lookup_emails,
)

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
    """Normalized inbox(es) for the user plus Gmail/GoogleMail aliases (dots, +tags, domains)."""
    raw_list: list[str] = []
    resolved = resolve_email_from_db_and_clerk(user.clerk_id, user.email)
    if resolved and "@" in resolved:
        raw_list.append(normalize_customer_email(resolved))
    if user.email and "@" in user.email:
        raw_list.append(normalize_customer_email(user.email))
    seen: set[str] = set()
    out: list[str] = []
    for x in raw_list:
        if not x:
            continue
        for cand in _candidate_lookup_emails(x):
            if cand and cand not in seen:
                seen.add(cand)
                out.append(cand)
    return out


def _support_thread_email_candidates(db: Session, user: User) -> list[str]:
    """Union profile emails with any customer_email ever logged for this user_id (reply aliases, Gmail variants)."""
    base = _customer_email_candidates(user)
    seen: set[str] = set(base)
    ordered = list(base)
    for (em,) in (
        db.query(SupportEmailLog.customer_email)
        .filter(SupportEmailLog.user_id == user.id)
        .distinct()
        .all()
    ):
        if not em:
            continue
        for cand in _candidate_lookup_emails(normalize_customer_email(em)):
            if cand not in seen:
                seen.add(cand)
                ordered.append(cand)
    return ordered


def _meta_as_dict(meta: object) -> dict | None:
    if meta is None:
        return None
    if isinstance(meta, dict):
        return meta
    if isinstance(meta, str):
        try:
            parsed = json.loads(meta)
            return parsed if isinstance(parsed, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def _legacy_dashboard_thread_rows(
    db: Session,
    user: User,
    *,
    exclude_ids: set[int],
    scan_limit: int = 200,
) -> list[SupportEmailLog]:
    """
    Dashboard rows saved before user_id was populated on SupportEmailLog.
    Resolved in Python to avoid PostgreSQL JSON path SQL that returned 500 on Azure.
    """
    q = (
        db.query(SupportEmailLog)
        .filter(SupportEmailLog.direction.in_(["inbound", "outbound"]))
        .filter(SupportEmailLog.channel == "user_dashboard")
        .order_by(SupportEmailLog.created_at.desc())
        .limit(scan_limit)
    )
    if exclude_ids:
        q = q.filter(~SupportEmailLog.id.in_(exclude_ids))
    matched: list[SupportEmailLog] = []
    for row in q.all():
        m = _meta_as_dict(row.meta)
        if not m or m.get("source") != "dashboard_contact":
            continue
        if str(m.get("user_id")) != str(user.id):
            continue
        matched.append(row)
    matched.sort(key=lambda r: (r.created_at.timestamp() if r.created_at else 0.0, r.id))
    return matched


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
    candidates = _support_thread_email_candidates(db, user)
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

    seen_ids = {r.id for r in rows}
    rows.extend(_legacy_dashboard_thread_rows(db, user, exclude_ids=seen_ids))
    rows.sort(key=lambda r: (r.created_at.timestamp() if r.created_at else 0.0, r.id))
    if len(rows) > limit:
        rows = rows[:limit]

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
        user_id=user.id,
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
