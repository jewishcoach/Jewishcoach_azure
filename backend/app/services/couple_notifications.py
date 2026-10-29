"""
Couple process emails: status only — never content, not even the shared title (a family inbox may be shared) —
and a link back to the app. Sent from BackgroundTasks with plain values (the request's DB session is gone by then).
"""
import html
import logging
from dataclasses import dataclass
from typing import Optional

from ..dependencies import resolve_email_from_db_and_clerk
from ..email_visibility import normalize_public_email
from ..models import User
from .email_service import send_html_email_detailed
from .onboarding_email_runtime import public_app_url

logger = logging.getLogger(__name__)


@dataclass
class Recipient:
    clerk_id: str
    email: Optional[str]


def recipient(user: User) -> Recipient:
    return Recipient(clerk_id=user.clerk_id, email=user.email)


def _send(to: Recipient, subject: str, lines: list[str]) -> None:
    address = normalize_public_email((resolve_email_from_db_and_clerk(to.clerk_id, to.email) or "").strip() or None)
    if not address:
        return  # no real inbox (Clerk placeholder) — the waiting screen still opens the shared screen by itself
    link = f"{public_app_url()}/?v3"
    body = "".join(f"<p>{html.escape(line)}</p>" for line in lines)
    html_body = (f'<div dir="rtl" style="font-family:Arial,sans-serif;font-size:16px;color:#2d4658;line-height:1.6">{body}'
                 f'<p><a href="{html.escape(link, quote=True)}">לכניסה לאפליקציה</a></p></div>')
    ok, err = send_html_email_detailed(address, subject, html_body, "\n".join([*lines, link]))
    if not ok:
        logger.warning("[Couple] email '%s' not sent: %s", subject, err)


def _g(gender: Optional[str]):
    return lambda m, f: f if gender == "female" else m


def send_partner_joined(to: Recipient, partner_name: str, partner_gender: Optional[str]) -> None:
    gp = _g(partner_gender)
    _send(to, f"{partner_name} {gp('הצטרף', 'הצטרפה')} לתהליך הזוגי", [
        f"{partner_name} {gp('הצטרף', 'הצטרפה')} לתהליך הזוגי שפתחת.",
        "כל אחד עובד עכשיו לבד, בקצב שלו. כששניכם תסיימו את שלב הגילוי, ייפתח לכם מסך השיתוף.",
    ])


def send_screen_open(to: Recipient, partner_name: str, partner_gender: Optional[str], checkpoint: str) -> None:
    gp = _g(partner_gender)
    screen = "מסך השיתוף" if checkpoint == "mirror" else "מסך ההתחייבות הזוגית"
    _send(to, f"{screen} שלכם פתוח", [
        f"{partner_name} {gp('סיים', 'סיימה')} את החלק {gp('שלו', 'שלה')}, ו{screen} שלכם פתוח באפליקציה.",
    ])
