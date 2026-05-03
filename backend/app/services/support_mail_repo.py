"""Shared DB helpers for support email audit logs."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import SupportEmailLog, User


def normalize_customer_email(email: str) -> str:
    return (email or "").strip().lower()


def resolve_user_id_for_email(db: Session, customer_email: str) -> Optional[int]:
    norm = normalize_customer_email(customer_email)
    if not norm or "@" not in norm:
        return None
    u = db.query(User.id).filter(User.email.isnot(None)).filter(User.email == norm).first()
    if u:
        return int(u[0])
    u2 = db.query(User.id).filter(func.lower(User.email) == norm).first()
    return int(u2[0]) if u2 else None


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

