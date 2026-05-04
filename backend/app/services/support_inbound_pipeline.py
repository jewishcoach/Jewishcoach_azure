"""Inbound support mailbox → audit log + optional AI auto-reply."""

from __future__ import annotations

import html
import os
import re
from email.utils import parseaddr
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models import SupportCustomerServiceSettings
from .email_service import send_html_email_detailed
from .support_customer_context import build_customer_support_snapshot
from .support_auto_reply_env import effective_auto_reply_enabled
from .support_mail_repo import (
    append_support_email_log,
    fetch_support_email_thread_for_llm,
    find_log_by_smtp_message_id,
    normalize_customer_email,
)
from .support_reply_ai import generate_support_reply_draft

_SETTINGS_ID = 1


def parse_sender_email(from_field: str) -> tuple[str, str]:
    """Returns (display_name_or_empty, email_lower)."""
    raw = (from_field or "").strip()
    name, addr = parseaddr(raw)
    norm = normalize_customer_email(addr)
    return (name or "").strip(), norm


def extract_reply_to_from_headers(headers_raw: Optional[str]) -> Optional[str]:
    """First mailbox from Reply-To (handles simple folded continuation lines)."""
    if not headers_raw or not headers_raw.strip():
        return None
    lines = headers_raw.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.lower().startswith("reply-to:"):
            i += 1
            continue
        chunks = [line.split(":", 1)[1].strip()]
        i += 1
        while i < len(lines) and lines[i] and lines[i][0] in " \t":
            chunks.append(lines[i].strip())
            i += 1
        combined = " ".join(chunks)
        for part in combined.split(","):
            _, addr = parseaddr(part.strip())
            norm = normalize_customer_email(addr)
            if norm and "@" in norm:
                return norm
        continue
    return None


def extract_reply_to_from_dashboard_body(text_part: Optional[str], html_part: Optional[str]) -> Optional[str]:
    """Parse Reply-To from dashboard HTML/plain templates (support_user_contact)."""
    html_blob = html_part or ""
    if html_blob.strip():
        m = re.search(r"<strong>\s*Reply-To:\s*</strong>\s*([^<\n]+)", html_blob, re.I)
        if m:
            _, addr = parseaddr(m.group(1).strip())
            norm = normalize_customer_email(addr)
            if norm and "@" in norm:
                return norm
    plain = (text_part or "").strip()
    if plain:
        m = re.search(r"(?im)^Reply-To:\s*(.+)$", plain)
        if m:
            _, addr = parseaddr(m.group(1).strip())
            norm = normalize_customer_email(addr)
            if norm and "@" in norm:
                return norm
    return None


def _support_mailbox_norm() -> str:
    return normalize_customer_email(os.getenv("SUPPORT_INBOUND_MAILBOX", "support@jewishcoacher.com"))


def _reply_to_is_customer_identity(reply_to: str, support_mailbox_norm: str) -> bool:
    """False when Reply-To is just our support inbox (mis-route)."""
    rt = normalize_customer_email(reply_to)
    if not rt or "@" not in rt:
        return False
    if support_mailbox_norm and rt == support_mailbox_norm:
        return False
    return True


def _configured_sender_email_norm() -> Optional[str]:
    raw = (os.getenv("EMAIL_SENDER") or "").strip()
    if not raw or "@" not in raw:
        return None
    _, addr = parseaddr(raw)
    norm = normalize_customer_email(addr)
    return norm if norm and "@" in norm else None


def _is_relay_mail_from(from_email: str) -> bool:
    """
    True when visible From is our transactional MAIL FROM (ACS provisional domain, etc.)
    and the real customer inbox is expected on Reply-To / body.
    """
    em = normalize_customer_email(from_email)
    if not em:
        return False
    if em.endswith(".azurecomm.net"):
        return True
    cfg = _configured_sender_email_norm()
    if cfg and em == cfg:
        return True
    return False


def resolve_inbound_customer_email(
    *,
    from_field: str,
    headers_raw: Optional[str],
    text_part: Optional[str],
    html_part: Optional[str],
) -> tuple[Optional[str], Optional[str], str]:
    """
    Map inbound message to a customer inbox for logging + auto-reply.

    Returns (normalized_customer_email or None, skip_reason or None, identity_source).
    identity_source is one of: from, reply_to_header, dashboard_body_reply_to, skipped.
    """
    _, from_email = parse_sender_email(from_field)
    if not from_email or "@" not in from_email:
        return None, "invalid_sender", "skipped"

    support_n = _support_mailbox_norm()

    if _is_relay_mail_from(from_email):
        rt_h = extract_reply_to_from_headers(headers_raw)
        if rt_h and _reply_to_is_customer_identity(rt_h, support_n):
            return normalize_customer_email(rt_h), None, "reply_to_header"
        rt_b = extract_reply_to_from_dashboard_body(text_part, html_part)
        if rt_b and _reply_to_is_customer_identity(rt_b, support_n):
            return normalize_customer_email(rt_b), None, "dashboard_body_reply_to"
        return None, "relay_sender_no_customer_reply_to", "skipped"

    skip = should_skip_customer(from_email)
    if skip:
        return None, skip, "skipped"
    return from_email, None, "from"


def extract_message_id_from_headers(headers_raw: Optional[str]) -> Optional[str]:
    if not headers_raw or not headers_raw.strip():
        return None
    for line in headers_raw.replace("\r\n", "\n").split("\n"):
        low = line.lower()
        if low.startswith("message-id:"):
            return line.split(":", 1)[1].strip().strip("<>")
    return None


def plain_text_from_parts(text: Optional[str], html_part: Optional[str]) -> str:
    t = (text or "").strip()
    if t:
        return t
    h = html_part or ""
    if not h.strip():
        return ""
    plain = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    plain = re.sub(r"(?s)<[^>]+>", " ", plain)
    plain = re.sub(r"\s+", " ", plain).strip()
    return html.unescape(plain)


def plain_to_reply_html(body_plain: str, *, rtl: bool = True) -> str:
    """Wrap plain text as HTML. For Hebrew, force RTL on html/body/wrapper — many clients ignore dir on <html> alone."""
    escaped_lines = []
    for line in (body_plain or "").split("\n"):
        escaped_lines.append(html.escape(line, quote=False))
    inner = "<br/>\n".join(escaped_lines)
    if rtl:
        html_open = '<html dir="rtl" lang="he">'
        body_style = (
            "font-family: Heebo, Arial, sans-serif; line-height: 1.65; color: #2E3A56; "
            "max-width: 560px; margin: 0 auto; padding: 20px; direction: rtl; text-align: start;"
        )
        wrap_open = '<div dir="rtl" style="direction: rtl; text-align: start;">'
        wrap_close = "</div>"
        footer = """  <p dir="rtl" style="color: #64748b; font-size: 12px; margin-top: 24px; direction: rtl; text-align: start;">
    Jewish Coach · תמיכה<br/>
    <a href="https://jewishcoacher.com" style="color: #B38728;">jewishcoacher.com</a>
  </p>"""
    else:
        html_open = '<html lang="en" dir="ltr">'
        body_style = (
            "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.65; color: #2E3A56; "
            "max-width: 560px; margin: 0 auto; padding: 20px; direction: ltr; text-align: start;"
        )
        wrap_open = '<div dir="ltr" style="direction: ltr; text-align: start;">'
        wrap_close = "</div>"
        footer = """  <p dir="ltr" style="color: #64748b; font-size: 12px; margin-top: 24px; direction: ltr; text-align: start;">
    Jewish Coach · Support<br/>
    <a href="https://jewishcoacher.com" style="color: #B38728;">jewishcoacher.com</a>
  </p>"""

    return f"""<!DOCTYPE html>
{html_open}
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="{body_style}">
  {wrap_open}
  {inner}
  {wrap_close}
{footer}
</body>
</html>
"""


def detect_language_hint(text: str) -> str:
    if re.search(r"[\u0590-\u05FF]", text or ""):
        return "he"
    return "en"


def mailbox_matches_recipient(to_field: str, expected_mailbox: str) -> bool:
    exp = normalize_customer_email(expected_mailbox)
    if not exp:
        return True
    low = (to_field or "").lower()
    return exp in low


def should_skip_customer(sender_email: str) -> Optional[str]:
    s = (sender_email or "").lower()
    if not s or "@" not in s:
        return "invalid_sender"
    if "mailer-daemon" in s or s.startswith("postmaster@"):
        return "bounce_or_system"
    if "noreply" in s or "no-reply" in s:
        return "noreply_sender"
    return None


def _get_settings_row(db: Session) -> SupportCustomerServiceSettings:
    row = db.query(SupportCustomerServiceSettings).filter(SupportCustomerServiceSettings.id == _SETTINGS_ID).first()
    if row:
        return row
    row = SupportCustomerServiceSettings(id=_SETTINGS_ID)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def process_inbound_support_email(
    db: Session,
    *,
    from_field: str,
    to_field: str,
    subject: str,
    text_part: Optional[str],
    html_part: Optional[str],
    headers_raw: Optional[str],
    mailbox_must_match: Optional[str] = None,
    message_id_override: Optional[str] = None,
    inbound_channel: str = "sendgrid_inbound",
) -> dict[str, Any]:
    """
    Idempotent when Message-ID is present and stored on first inbound log.
    """
    expected_mailbox = (mailbox_must_match or os.getenv("SUPPORT_INBOUND_MAILBOX", "support@jewishcoacher.com")).strip()
    if expected_mailbox and not mailbox_matches_recipient(to_field, expected_mailbox):
        return {"skipped": True, "reason": "recipient_not_support_mailbox", "expected": expected_mailbox}

    msg_id = (message_id_override or "").strip() or extract_message_id_from_headers(headers_raw)
    msg_id = msg_id.strip().strip("<>") if msg_id else None
    if msg_id and find_log_by_smtp_message_id(db, msg_id):
        return {"skipped": True, "reason": "duplicate_message_id", "smtp_message_id": msg_id}

    customer_email, cust_skip, identity_src = resolve_inbound_customer_email(
        from_field=from_field,
        headers_raw=headers_raw,
        text_part=text_part,
        html_part=html_part,
    )
    if cust_skip:
        return {"skipped": True, "reason": cust_skip}

    body_plain = plain_text_from_parts(text_part, html_part)
    if not body_plain:
        return {"skipped": True, "reason": "empty_body"}

    subj = (subject or "").strip() or "(ללא נושא)"
    _, envelope_from = parse_sender_email(from_field)

    inbound_row = append_support_email_log(
        db,
        customer_email=customer_email,
        direction="inbound",
        channel=inbound_channel,
        subject=subj,
        body=body_plain,
        meta={
            "to": to_field[:500] if to_field else None,
            "envelope_from": envelope_from,
            "customer_identity_source": identity_src,
        },
        smtp_message_id=msg_id,
    )

    settings = _get_settings_row(db)
    auto_reply = effective_auto_reply_enabled(settings)

    snapshot = build_customer_support_snapshot(db, customer_email)
    lang = detect_language_hint(body_plain + " " + subj)

    prior_thread = fetch_support_email_thread_for_llm(db, customer_email, exclude_log_id=inbound_row.id)

    try:
        draft = generate_support_reply_draft(
            customer_snapshot=snapshot,
            incoming_message=f"נושא / Subject: {subj}\n\n{body_plain}",
            personality_text=settings.personality_text,
            terms_text=settings.terms_and_boundaries_text,
            methodology_text=settings.methodology_context_text,
            language=lang,
            prior_support_email_thread=prior_thread,
        )
    except Exception as e:
        append_support_email_log(
            db,
            customer_email=customer_email,
            direction="draft",
            channel="auto_reply_failed",
            subject=subj,
            body=str(e),
            meta={"inbound_log_id": inbound_row.id},
            smtp_message_id=None,
        )
        return {
            "skipped": False,
            "inbound_log_id": inbound_row.id,
            "auto_reply": False,
            "error": f"llm: {e!s}",
        }

    draft_meta: dict[str, Any] = {"inbound_log_id": inbound_row.id}
    if draft.internal_notes:
        draft_meta["internal_notes"] = draft.internal_notes

    append_support_email_log(
        db,
        customer_email=customer_email,
        direction="draft",
        channel="ai_draft_auto",
        subject=draft.subject.strip() or None,
        body=draft.body_plain.strip(),
        meta=draft_meta,
        smtp_message_id=None,
    )

    if not auto_reply:
        return {
            "skipped": False,
            "inbound_log_id": inbound_row.id,
            "auto_reply": False,
            "draft_subject": draft.subject,
            "note": "auto_reply_disabled_in_admin_settings",
        }

    reply_subj = (draft.subject or "").strip() or f"Re: {subj}"
    reply_plain = (draft.body_plain or "").strip()
    if not reply_plain:
        return {"skipped": False, "inbound_log_id": inbound_row.id, "auto_reply": False, "error": "empty_draft"}

    suffix_he = "\n\n—\nתשובה אוטומטית שנוצרה באמצעות AI; אם צריך צוות אנושי נשמח להמשיך כאן באימייל."
    suffix_en = "\n\n—\nThis message was drafted automatically; our team can follow up by email if needed."
    reply_plain_full = reply_plain + (suffix_he if lang.startswith("he") else suffix_en)

    rtl = lang.startswith("he") or bool(re.search(r"[\u0590-\u05FF]", reply_plain_full))
    reply_html = plain_to_reply_html(reply_plain_full, rtl=rtl)

    ok, send_err = send_html_email_detailed(customer_email, reply_subj, reply_html, body_plain=reply_plain_full)
    out_meta: dict[str, Any] = {"inbound_log_id": inbound_row.id, "send_ok": ok, "to": customer_email}
    if not ok:
        out_meta["send_error"] = (send_err or "unknown_send_failure").strip()[:2000]
    append_support_email_log(
        db,
        customer_email=customer_email,
        direction="outbound",
        channel="auto_reply",
        subject=reply_subj,
        body=reply_plain_full,
        meta=out_meta,
        smtp_message_id=None,
    )

    return {
        "skipped": False,
        "inbound_log_id": inbound_row.id,
        "auto_reply": True,
        "sent": ok,
        "send_error": (send_err or ("unknown_send_failure" if not ok else None)),
        "reply_subject": reply_subj,
    }

