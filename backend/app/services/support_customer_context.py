"""Build a compact JSON snapshot of a customer for support AI (DB-backed)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Conversation, CouponRedemption, Subscription, UsageRecord, User


def _active_coupon(db: Session, user_id: int) -> bool:
    now = datetime.now(timezone.utc)
    row = (
        db.query(CouponRedemption.id)
        .filter(
            CouponRedemption.user_id == user_id,
            CouponRedemption.is_active.is_(True),
        )
        .filter(
            (CouponRedemption.expires_at.is_(None)) | (CouponRedemption.expires_at > now),
        )
        .first()
    )
    return row is not None


def build_customer_support_snapshot(db: Session, customer_email: str) -> dict:
    raw = (customer_email or "").strip()
    norm = raw.lower()
    if not norm or "@" not in norm:
        return {"matched_user": False, "lookup_email": raw, "reason": "invalid_email"}

    user = db.query(User).filter(func.lower(User.email) == norm).first()
    if not user:
        return {
            "matched_user": False,
            "lookup_email": raw,
            "reason": "no_user_with_this_email_in_db",
        }

    subs = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id)
        .order_by(Subscription.updated_at.desc())
        .limit(8)
        .all()
    )
    convos = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(5)
        .all()
    )
    usage = (
        db.query(UsageRecord)
        .filter(UsageRecord.user_id == user.id)
        .order_by(UsageRecord.period_start.desc())
        .limit(3)
        .all()
    )

    return {
        "matched_user": True,
        "user_id": user.id,
        "email_in_db": user.email,
        "display_name": user.display_name,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "current_plan": (user.current_plan or "basic").strip() or "basic",
        "has_stripe_customer": bool(user.stripe_customer_id),
        "has_active_coupon": _active_coupon(db, user.id),
        "primary_discipline": user.primary_discipline,
        "subscriptions": [
            {
                "plan": s.plan,
                "status": s.status,
                "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
                "cancel_at_period_end": bool(s.cancel_at_period_end),
            }
            for s in subs
        ],
        "recent_conversations": [
            {
                "title": c.title,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                "phase": c.current_phase,
            }
            for c in convos
        ],
        "recent_usage_periods": [
            {
                "period_start": u.period_start.isoformat() if u.period_start else None,
                "period_end": u.period_end.isoformat() if u.period_end else None,
                "messages_used": u.messages_used,
                "speech_minutes_used": u.speech_minutes_used,
            }
            for u in usage
        ],
    }

