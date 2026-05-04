"""
Enqueue new users onto the default onboarding drip + process due sends.

Placeholders in subject/body: {{display_name}}, {{email}}, {{app_url}}
"""

from __future__ import annotations

import html
import os
import re
from datetime import timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..database import utc_now
from ..dependencies import resolve_email_from_db_and_clerk
from ..email_visibility import normalize_public_email
from ..models import (
    OnboardingEmailSequence,
    OnboardingEmailStep,
    User,
    UserOnboardingEmailState,
)
from .email_service import send_html_email


def resolve_onboarding_send_email(user: User) -> Optional[str]:
    """
    Inbox to use for onboarding transactional sends (same rules as template {{email}}).
    Requires real email on User or CLERK_SECRET_KEY for API fallback from clerk.temp.
    """
    raw = resolve_email_from_db_and_clerk(user.clerk_id, user.email)
    if not raw:
        return None
    s = raw.strip()
    if not s or "@" not in s:
        return None
    return normalize_public_email(s)


def public_app_url() -> str:
    return (os.getenv("PUBLIC_APP_URL") or os.getenv("VITE_APP_URL") or "https://jewishcoacher.com").strip().rstrip(
        "/"
    )


def render_onboarding_template(raw: str, user: User) -> str:
    if not raw:
        return ""
    vis = resolve_onboarding_send_email(user) or ""
    name = (user.display_name or "").strip() or "שם"
    email_s = vis or ""
    app = public_app_url()
    out = raw.replace("{{display_name}}", html.escape(name))
    out = out.replace("{{email}}", html.escape(email_s))
    out = out.replace("{{app_url}}", html.escape(app))
    return out


def _append_images_block(html_body: str, urls: Any) -> str:
    if not urls or not isinstance(urls, list):
        return html_body
    clean = [str(u).strip() for u in urls if isinstance(u, str) and u.strip()]
    if not clean:
        return html_body
    block = '<div style="margin-top:16px">' + "".join(
        f'<p style="margin:8px 0"><img src="{html.escape(u, quote=True)}" alt="" style="max-width:100%;border-radius:8px"/></p>'
        for u in clean
    )
    block += "</div>"
    return html_body + block


def build_final_html(step: OnboardingEmailStep, user: User) -> tuple[str, str, str]:
    subject = render_onboarding_template(step.subject, user)
    body = render_onboarding_template(step.body_html, user)
    body = _append_images_block(body, step.image_urls)
    wrapped = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"/></head>
<body style="font-family:Heebo,Arial,sans-serif;line-height:1.6;color:#2E3A56;max-width:560px;margin:0 auto;padding:24px;">
{body}
<p style="color:#64748b;font-size:12px;margin-top:28px;">Jewish Coach<br/><a href="{html.escape(public_app_url(), quote=True)}">{html.escape(public_app_url())}</a></p>
</body></html>"""
    plain_base = step.body_plain or re.sub(r"<[^>]+>", " ", body)
    plain_base = re.sub(r"\s+", " ", plain_base).strip()
    plain = render_onboarding_template(plain_base, user)
    return subject, wrapped, plain


def maybe_enqueue_default_sequence(db: Session, user: User) -> None:
    """Called once after a brand-new User row is committed."""
    try:
        existing = (
            db.query(UserOnboardingEmailState).filter(UserOnboardingEmailState.user_id == user.id).first()
        )
        if existing:
            return
        seq = (
            db.query(OnboardingEmailSequence)
            .filter(
                OnboardingEmailSequence.is_default.is_(True),
                OnboardingEmailSequence.is_active.is_(True),
            )
            .first()
        )
        if not seq:
            return
        steps = (
            db.query(OnboardingEmailStep)
            .filter(OnboardingEmailStep.sequence_id == seq.id)
            .order_by(OnboardingEmailStep.sort_order.asc())
            .all()
        )
        if not steps:
            return
        delay_min = max(0, int(steps[0].delay_after_previous_minutes or 0))
        next_at = utc_now() + timedelta(minutes=delay_min)
        row = UserOnboardingEmailState(
            user_id=user.id,
            sequence_id=seq.id,
            next_step_index=0,
            next_send_at=next_at,
            completed=False,
        )
        db.add(row)
        db.commit()
        print(f"📧 [OnboardingEmail] Enrolled user {user.id} in sequence '{seq.name}' (first send ~{delay_min}m)")
    except Exception as e:
        db.rollback()
        print(f"⚠️ [OnboardingEmail] enqueue skipped/failed for user {user.id}: {type(e).__name__}: {e}")


def enqueue_existing_users_missing_default_sequence(db: Session, *, limit: int = 2000) -> dict[str, Any]:
    """
    Backfill: users who never got UserOnboardingEmailState (signed up before drip existed).

    Safe to run multiple times — skips anyone already enrolled.
    """
    seq = (
        db.query(OnboardingEmailSequence)
        .filter(
            OnboardingEmailSequence.is_default.is_(True),
            OnboardingEmailSequence.is_active.is_(True),
        )
        .first()
    )
    if not seq:
        return {"enrolled": 0, "reason": "no_active_default_sequence"}
    steps = (
        db.query(OnboardingEmailStep)
        .filter(OnboardingEmailStep.sequence_id == seq.id)
        .order_by(OnboardingEmailStep.sort_order.asc())
        .all()
    )
    if not steps:
        return {"enrolled": 0, "reason": "sequence_has_no_steps"}

    enrolled_subq = db.query(UserOnboardingEmailState.user_id)
    candidates = (
        db.query(User)
        .filter(~User.id.in_(enrolled_subq))
        .order_by(User.id.asc())
        .limit(max(1, min(limit, 50_000)))
        .all()
    )
    delay_min = max(0, int(steps[0].delay_after_previous_minutes or 0))
    next_at = utc_now() + timedelta(minutes=delay_min)
    enrolled = 0
    for user in candidates:
        db.add(
            UserOnboardingEmailState(
                user_id=user.id,
                sequence_id=seq.id,
                next_step_index=0,
                next_send_at=next_at,
                completed=False,
            )
        )
        enrolled += 1
    db.commit()
    print(f"📧 [OnboardingEmail] Backfill enrolled {enrolled} users in '{seq.name}' (limit={limit})")
    return {
        "enrolled": enrolled,
        "sequence_id": seq.id,
        "sequence_name": seq.name,
        "first_send_after_minutes": delay_min,
    }


def onboarding_email_queue_stats(db: Session) -> dict[str, Any]:
    """Counts for admin/cron diagnostics."""
    now = utc_now()
    total_users = db.query(User).count()
    queue_rows = db.query(UserOnboardingEmailState).count()
    pending = (
        db.query(UserOnboardingEmailState)
        .filter(UserOnboardingEmailState.completed.is_(False))
        .count()
    )
    due_now = (
        db.query(UserOnboardingEmailState)
        .filter(
            UserOnboardingEmailState.completed.is_(False),
            UserOnboardingEmailState.next_send_at.isnot(None),
            UserOnboardingEmailState.next_send_at <= now,
        )
        .count()
    )
    approx_without_queue = max(0, total_users - queue_rows)
    return {
        "users_total": total_users,
        "queue_rows": queue_rows,
        "pending_incomplete": pending,
        "due_now": due_now,
        "approx_users_without_queue_row": approx_without_queue,
        "hint": "Use POST /api/admin/onboarding-email/enroll-missing-users if approx_users_without_queue_row is large; "
        "ensure cron hits POST /api/internal/onboarding-email/process-due with ONBOARDING_EMAIL_CRON_SECRET.",
    }


def process_due_onboarding_emails(db: Session, *, limit: int = 50) -> dict[str, Any]:
    """Send emails whose next_send_at is due; advance queue."""
    now = utc_now()
    states = (
        db.query(UserOnboardingEmailState)
        .filter(
            UserOnboardingEmailState.completed.is_(False),
            UserOnboardingEmailState.next_send_at.isnot(None),
            UserOnboardingEmailState.next_send_at <= now,
        )
        .order_by(UserOnboardingEmailState.next_send_at.asc())
        .limit(limit)
        .all()
    )
    sent = 0
    skipped = 0
    errors: list[str] = []

    for st in states:
        seq = db.query(OnboardingEmailSequence).filter(OnboardingEmailSequence.id == st.sequence_id).first()
        user = db.query(User).filter(User.id == st.user_id).first()
        if not seq or not user or not seq.is_active:
            st.completed = True
            st.next_send_at = None
            continue
        steps = (
            db.query(OnboardingEmailStep)
            .filter(OnboardingEmailStep.sequence_id == seq.id)
            .order_by(OnboardingEmailStep.sort_order.asc())
            .all()
        )
        if not steps:
            st.completed = True
            st.next_send_at = None
            continue
        idx = st.next_step_index
        if idx >= len(steps):
            st.completed = True
            st.next_send_at = None
            continue

        step = steps[idx]
        vis = resolve_onboarding_send_email(user)
        if not vis or "@" not in vis:
            skipped += 1
            st.next_send_at = now + timedelta(hours=2)
            errors.append(f"user {user.id}: no real inbox yet, deferred 2h")
            continue

        subject, html_body, plain = build_final_html(step, user)
        ok = send_html_email(vis, subject, html_body, plain)
        if not ok:
            skipped += 1
            st.next_send_at = now + timedelta(minutes=30)
            errors.append(f"user {user.id}: send failed, retry 30m")
            continue

        sent += 1
        next_idx = idx + 1
        st.next_step_index = next_idx
        if next_idx >= len(steps):
            st.completed = True
            st.next_send_at = None
        else:
            delay_next = max(0, int(steps[next_idx].delay_after_previous_minutes or 0))
            st.next_send_at = now + timedelta(minutes=delay_next)

    db.commit()
    return {"processed_states": len(states), "sent": sent, "skipped": skipped, "notes": errors[:20]}
