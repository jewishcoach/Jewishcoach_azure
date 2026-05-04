"""Shared DB helpers for support email audit logs."""

from __future__ import annotations

import json
import os
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from sqlalchemy import func, not_, or_
from sqlalchemy.orm import Session

from ..models import SupportEmailLog, User


_ZW_CHARS = ("\u200b", "\u200c", "\u200d", "\ufeff")


def normalize_customer_email(email: str) -> str:
    """Lowercase inbox address; strip whitespace, BOM/zero-width chars, Unicode-compat normalize."""
    s = (email or "").strip()
    for ch in _ZW_CHARS:
        s = s.replace(ch, "")
    s = unicodedata.normalize("NFKC", s).strip().lower()
    return s


def _gmail_local_bases(local: str) -> list[str]:
    """Gmail treats dots and plus-tags as aliases; expand local-part bases for lookup."""
    loc = (local or "").strip().lower()
    if not loc:
        return []
    bases = [loc]
    if "+" in loc:
        bases.append(loc.split("+", 1)[0])
    seen: set[str] = set()
    out: list[str] = []
    for b in bases:
        if b and b not in seen:
            seen.add(b)
            out.append(b)
    return out


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
        for loc in _gmail_local_bases(local):
            collapsed = loc.replace(".", "")
            for dom in ("gmail.com", "googlemail.com"):
                add(f"{loc}@{dom}")
                add(f"{collapsed}@{dom}")
    return ordered


def _user_email_not_placeholder():
    """Rows still carrying Clerk placeholders are not real inbox addresses."""
    return not_(or_(User.email.ilike("%@clerk.temp"), User.email.ilike("%@clerk.accounts.%")))


def _is_placeholder_email(email: Optional[str]) -> bool:
    em = (email or "").strip().lower()
    return bool(em) and (em.endswith("@clerk.temp") or "@clerk.accounts." in em)


def _maybe_upgrade_placeholder_email(db: Session, user: User, canonical_email: str) -> None:
    """Persist real inbox on rows that still only have Clerk synthetic emails."""
    if not canonical_email or "@" not in canonical_email:
        return
    if not _is_placeholder_email(user.email):
        return
    user.email = canonical_email
    db.add(user)
    db.commit()
    db.refresh(user)


def _clerk_user_ids_for_email(email: str) -> list[str]:
    """
    Clerk Backend API: users that own this email address.
    Needs CLERK_SECRET_KEY (same as JWT resolution). Used when DB.email is missing/out of sync.
    """
    secret = os.getenv("CLERK_SECRET_KEY", "").strip()
    if not secret or "@" not in email:
        return []

    def _parse_ids(payload: object) -> list[str]:
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        if not isinstance(data, list):
            return []
        ids: list[str] = []
        for item in data:
            if isinstance(item, dict):
                cid = item.get("id")
                if isinstance(cid, str) and cid.strip():
                    ids.append(cid.strip())
        return ids

    base = "https://api.clerk.com/v1/users"
    attempts: list[str] = []
    # Clerk accepts email_address (string or repeated); try common shapes.
    attempts.append(base + "?" + urllib.parse.urlencode({"email_address": email, "limit": "10"}))
    attempts.append(
        base
        + "?"
        + urllib.parse.urlencode([("email_address[]", email), ("limit", "10")])
    )

    for url in attempts:
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {secret}"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                body = json.loads(resp.read().decode())
            ids = _parse_ids(body)
            if ids:
                return ids
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode(errors="replace")[:200]
            except Exception:
                pass
            if e.code != 404:
                print(f"⚠️ [SUPPORT_EMAIL] Clerk user list HTTP {e.code}: {detail or e.reason}")
            continue
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"⚠️ [SUPPORT_EMAIL] Clerk user list failed: {type(e).__name__}: {e}")
            continue
    return []


def match_user_by_support_email(db: Session, customer_email: str) -> Optional[User]:
    """Resolve User row for inbound/support addressing (trim, case, Gmail dots/domain/+tag, Clerk fallback)."""
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

    # DB row may still be user_xxx@clerk.temp while the customer writes from their real inbox.
    seen_clerk: set[str] = set()
    for cand in _candidate_lookup_emails(norm):
        for clerk_id in _clerk_user_ids_for_email(cand):
            if clerk_id in seen_clerk:
                continue
            seen_clerk.add(clerk_id)
            row = db.query(User).filter(User.clerk_id == clerk_id).first()
            if row:
                _maybe_upgrade_placeholder_email(db, row, norm)
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


def _truncate_body(text: str, max_len: int) -> str:
    s = (text or "").strip()
    if max_len <= 0:
        return ""
    if len(s) <= max_len:
        return s
    return s[: max_len - 3].rstrip() + "..."


def fetch_support_email_thread_for_llm(
    db: Session,
    customer_email: str,
    *,
    exclude_log_id: Optional[int] = None,
    max_messages: Optional[int] = None,
    max_total_chars: Optional[int] = None,
    max_body_per_message: Optional[int] = None,
) -> list[dict[str, Any]]:
    """
    Prior support mailbox messages for one customer, chronological (oldest → newest).

    Used as LLM context. Caps message count and total text (env SUPPORT_THREAD_*).
    exclude_log_id: omit this log row (e.g. the inbound message being answered now).
    """
    norm = normalize_customer_email(customer_email)
    if not norm or "@" not in norm:
        return []

    mm = max_messages if max_messages is not None else int(os.getenv("SUPPORT_THREAD_MAX_MESSAGES", "40"))
    mt = max_total_chars if max_total_chars is not None else int(os.getenv("SUPPORT_THREAD_MAX_CHARS", "28000"))
    mb = max_body_per_message if max_body_per_message is not None else int(
        os.getenv("SUPPORT_THREAD_MAX_BODY_PER_MESSAGE", "8000")
    )

    q = db.query(SupportEmailLog).filter(SupportEmailLog.customer_email == norm)
    if exclude_log_id is not None:
        q = q.filter(SupportEmailLog.id != exclude_log_id)
    rows = q.order_by(SupportEmailLog.created_at.desc(), SupportEmailLog.id.desc()).limit(mm).all()
    rows_chrono = list(reversed(rows))

    out: list[dict[str, Any]] = []
    for row in rows_chrono:
        out.append(
            {
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "direction": row.direction,
                "channel": row.channel,
                "subject": (row.subject or "").strip() or None,
                "body": _truncate_body(row.body or "", mb),
            }
        )

    def approx_chars(items: list[dict[str, Any]]) -> int:
        n = 0
        for x in items:
            n += len(str(x.get("body") or ""))
            n += len(str(x.get("subject") or ""))
            n += len(str(x.get("direction") or ""))
            n += len(str(x.get("channel") or ""))
        return n

    while len(out) > 1 and approx_chars(out) > mt:
        out.pop(0)

    return out


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

