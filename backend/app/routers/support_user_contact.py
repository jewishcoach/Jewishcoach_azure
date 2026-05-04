"""Authenticated dashboard → support inbox contact form."""

from __future__ import annotations

import html
import json
import logging
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

logger = logging.getLogger(__name__)

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


def _utf8_safe(text: str | None, max_len: int | None = None) -> str:
    """Avoid UnicodeEncodeError / surrogates breaking FastAPI JSONResponse."""
    s = "" if text is None else str(text)
    s = s.encode("utf-8", errors="replace").decode("utf-8")
    if max_len is not None and len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s


def _safe_created_ts(dt: object) -> float:
    if dt is None or not hasattr(dt, "timestamp"):
        return 0.0
    try:
        return float(dt.timestamp())  # type: ignore[union-attr]
    except (OSError, OverflowError, ValueError):
        return 0.0


def _safe_created_iso(dt: object) -> str | None:
    if dt is None or not hasattr(dt, "isoformat"):
        return None
    try:
        return dt.isoformat()  # type: ignore[union-attr]
    except (OSError, ValueError):
        return None


def _meta_as_dict(meta: object) -> dict | None:
    if meta is None:
        return None
    if isinstance(meta, dict):
        return meta
    if isinstance(meta, (bytes, bytearray)):
        try:
            meta = meta.decode("utf-8", errors="replace")
        except Exception:
            return None
    if isinstance(meta, memoryview):
        try:
            meta = meta.tobytes().decode("utf-8", errors="replace")
        except Exception:
            return None
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
        try:
            m = _meta_as_dict(row.meta)
            if not m or m.get("source") != "dashboard_contact":
                continue
            if str(m.get("user_id")) != str(user.id):
                continue
            matched.append(row)
        except Exception:
            logger.warning("support_thread skipped legacy candidate row id=%s", getattr(row, "id", "?"), exc_info=True)
    matched.sort(key=lambda r: (_safe_created_ts(r.created_at), r.id))
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
    body = _utf8_safe(row.body, 12_000)
    subject = row.subject
    subject_out = _utf8_safe(subject, 500) if subject else None
    ts = _safe_created_iso(row.created_at)
    return {
        "id": row.id,
        "direction": _utf8_safe(row.direction, 128),
        "channel": _utf8_safe(row.channel, 128),
        "subject": subject_out,
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
    try:
        candidates = _support_thread_email_candidates(db, user)
    except Exception:
        logger.exception("support_thread email candidates failed")
        candidates = []

    conds = [SupportEmailLog.user_id == user.id]
    if candidates:
        conds.append(SupportEmailLog.customer_email.in_(candidates))

    try:
        primary_rows = (
            db.query(SupportEmailLog)
            .filter(or_(*conds))
            .filter(SupportEmailLog.direction.in_(["inbound", "outbound"]))
            .order_by(SupportEmailLog.created_at.asc(), SupportEmailLog.id.asc())
            .limit(limit)
            .all()
        )
    except Exception:
        logger.exception("support_thread primary query failed")
        primary_rows = []

    seen_ids = {r.id for r in primary_rows}
    legacy_rows: list[SupportEmailLog] = []
    try:
        legacy_rows = _legacy_dashboard_thread_rows(db, user, exclude_ids=seen_ids)
    except Exception:
        logger.exception("support_thread legacy scan failed")

    by_id: dict[int, SupportEmailLog] = {r.id: r for r in primary_rows}
    for r in legacy_rows:
        by_id[r.id] = r
    merged = sorted(by_id.values(), key=lambda r: (_safe_created_ts(r.created_at), r.id))
    if len(merged) > limit:
        merged = merged[:limit]

    items: list[dict] = []
    for r in merged:
        try:
            items.append(_serialize_log_row(r))
        except Exception:
            logger.warning("support_thread serialize skip id=%s", getattr(r, "id", "?"), exc_info=True)

    return {"items": items}


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
