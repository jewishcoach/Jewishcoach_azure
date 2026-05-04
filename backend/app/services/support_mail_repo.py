"""Shared DB helpers for support email audit logs."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, not_, or_
from sqlalchemy.orm import Session

from ..models import SupportEmailLog, User


def normalize_customer_email(email: str) -> str:
    return (email or "").strip().lower()


def _candidate_lookup_emails(norm: str) -> list[str]:
    """Variants to try against DB (trim/lowercase already applied to norm)."""
    norm = (norm or "").strip().lower()
    if not norm or "@" not in norm:
        return []
    local, _, domain = norm.partition("@")
    seen: set[str] = set()
    ordered: list[str] = []

    def add(x: str) -> None:
        x = x.strip().lower()
        if x and x not in seen:
            seen.add(x)
            ordered.append(x)

    add(norm)
    if domain in ("gmail.com", "googlemail.com"):
        collapsed = local.replace(".", "")
        for dom in ("gmail.com", "googlemail.com"):
            add(f"{local}@{dom}")
            add(f"{collapsed}@{dom}")
    return ordered


def _user_email_not_placeholder():
    """Rows still carrying Clerk placeholders are not real inbox addresses."""
    return not_(or_(User.email.ilike("%@clerk.temp"), User.email.ilike("%@clerk.accounts.%")))


def match_user_by_support_email(db: Session, customer_email: str) -> Optional[User]:
    """Resolve User row for inbound/support addressing (trim, case, Gmail dots/domain)."""
    norm = normalize_customer_email(customer_email)
    if not norm or "@" not in norm:
        return None
    for cand in _candidate_lookup_emails(norm):
        row = (
            db.query(User)
            .filter(User.email.isnot(None))
            .filter(_user_email_not_placeholder())
            .filter(func.lower(func.trim(User.email)) == cand)
            .first()
        )
        if row:
            return row
    return None


def resolve_user_id_for_email(db: Session, customer_email: str) -> Optional[int]:
    user = match_user_by_support_email(db, customer_email)
    return int(user.id) if user else None


def find_log_by_smtp_message_id(db: Session, smtp_message_id: Optional[str]) -> Optional[SupportEmailLog]:
    if not smtp_message_id or not smtp_message_id.strip():
        return None
    mid = smtp_message_id.strip()
    return db.query(SupportEmailLog).filter(SupportEmailLog.smtp_message_id == mid).first()


def append_support_email_log(
    db: Session,
    *,
    customer_email: str,
    direction: str,
    channel: str,
    subject: Optional[str],
    body: str,
    meta: Optional[dict[str, Any]] = None,
    smtp_message_id: Optional[str] = None,
) -> SupportEmailLog:
    norm = normalize_customer_email(customer_email)
    uid = resolve_user_id_for_email(db, norm)
    row = SupportEmailLog(
        user_id=uid,
        customer_email=norm,
        direction=direction,
        channel=channel,
        subject=(subject or "").strip() or None,
        body=body,
        meta=meta or {},
        smtp_message_id=smtp_message_id.strip() if smtp_message_id and smtp_message_id.strip() else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

