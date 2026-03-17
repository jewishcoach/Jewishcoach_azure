"""
Email service for sending reminder notifications.
Supports Azure Communication Services Email (preferred) or SendGrid.
Sender: reminders@jewishcoacher.com
"""
import os
from datetime import datetime
from typing import Optional

SENDER_EMAIL = os.getenv("EMAIL_SENDER", "reminders@jewishcoacher.com")
SENDER_NAME = "Jewish Coach - תזכורות אימון"


def _build_reminder_content(
    title: str,
    description: Optional[str],
    reminder_date: datetime,
    reminder_time: Optional[str],
    repeat_type: str,
) -> tuple[str, str]:
    """Build subject, plain text and HTML for reminder email."""
    date_str = reminder_date.strftime("%d/%m/%Y")
    time_str = reminder_time or "00:00"
    repeat_labels = {
        "once": "פעם אחת",
        "daily": "יומי",
        "weekly": "שבועי",
        "biweekly": "דו-שבועי",
        "monthly": "חודשי",
    }
    repeat_str = repeat_labels.get(repeat_type, repeat_type)

    subject = f"תזכורת: {title}"
    body_plain = f"""שלום,

זו תזכורת לאימון שלך:

כותרת: {title}
תאריך: {date_str}
שעה: {time_str}
חזרה: {repeat_str}
"""
    if description:
        body_plain += f"\nתיאור: {description}\n"

    body_plain += """
---
Jewish Coach - אימון יהודי
https://jewishcoacher.com
"""

    body_html = f"""
<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="utf-8"></head>
<body style="font-family: Heebo, Arial, sans-serif; line-height: 1.6; color: #2E3A56; max-width: 500px; margin: 0 auto; padding: 20px;">
  <p>שלום,</p>
  <p>זו תזכורת לאימון שלך:</p>
  <div style="background: #f5f5f0; padding: 16px; border-radius: 8px; margin: 16px 0;">
    <p style="margin: 0 0 8px 0;"><strong>כותרת:</strong> {title}</p>
    <p style="margin: 0 0 8px 0;"><strong>תאריך:</strong> {date_str}</p>
    <p style="margin: 0 0 8px 0;"><strong>שעה:</strong> {time_str}</p>
    <p style="margin: 0 0 8px 0;"><strong>חזרה:</strong> {repeat_str}</p>
    {f'<p style="margin: 0;"><strong>תיאור:</strong> {description}</p>' if description else ''}
  </div>
  <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
    Jewish Coach - אימון יהודי<br>
    <a href="https://jewishcoacher.com" style="color: #B38728;">jewishcoacher.com</a>
  </p>
</body>
</html>
"""
    return subject, body_plain, body_html


def _send_via_azure(subject: str, body_plain: str, body_html: str, to_email: str) -> bool:
    """Send via Azure Communication Services Email."""
    conn_str = os.getenv("EMAIL_CONNECTION_STRING", "").strip()
    if not conn_str:
        return False
    try:
        from azure.communication.email import EmailClient
        client = EmailClient.from_connection_string(conn_str)
        message = {
            "content": {
                "subject": subject,
                "plainText": body_plain,
                "html": body_html,
            },
            "recipients": {"to": [{"address": to_email}]},
            "senderAddress": SENDER_EMAIL,
        }
        poller = client.begin_send(message)
        poller.result()
        return True
    except Exception as e:
        print(f"[EMAIL Azure] Failed to send to {to_email}: {e}")
        return False


def _send_via_sendgrid(subject: str, body_plain: str, body_html: str, to_email: str) -> bool:
    """Send via SendGrid."""
    api_key = os.getenv("SENDGRID_API_KEY", "").strip()
    if not api_key:
        return False
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content
        message = Mail(
            from_email=Email(SENDER_EMAIL, SENDER_NAME),
            to_emails=To(to_email),
            subject=subject,
            plain_text_content=Content("text/plain", body_plain),
            html_content=Content("text/html", body_html),
        )
        sg = SendGridAPIClient(api_key)
        sg.send(message)
        return True
    except Exception as e:
        print(f"[EMAIL SendGrid] Failed to send to {to_email}: {e}")
        return False


def send_reminder_email(
    to_email: str,
    title: str,
    description: Optional[str],
    reminder_date: datetime,
    reminder_time: Optional[str],
    repeat_type: str = "once",
) -> bool:
    """
    Send a coaching reminder email.
    Uses Azure Communication Services if EMAIL_CONNECTION_STRING is set,
    otherwise SendGrid if SENDGRID_API_KEY is set.
    Returns True if sent successfully, False otherwise.
    """
    subject, body_plain, body_html = _build_reminder_content(
        title, description, reminder_date, reminder_time, repeat_type
    )

    if os.getenv("EMAIL_CONNECTION_STRING", "").strip():
        ok = _send_via_azure(subject, body_plain, body_html, to_email)
    elif os.getenv("SENDGRID_API_KEY", "").strip():
        ok = _send_via_sendgrid(subject, body_plain, body_html, to_email)
    else:
        print("[EMAIL] Neither EMAIL_CONNECTION_STRING nor SENDGRID_API_KEY set - skipping")
        return False

    if ok:
        print(f"[EMAIL] Sent reminder '{title}' to {to_email}")
    return ok
