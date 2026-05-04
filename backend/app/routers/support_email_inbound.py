"""
Inbound webhook for customer-support mailbox.

1) SendGrid-style multipart/form-data → POST /api/internal/support-email/inbound
2) Make / Zapier / custom HTTP (JSON) → POST /api/internal/support-email/inbound-json

Set SUPPORT_INBOUND_WEBHOOK_SECRET on the App Service.

Header on both routes:
    X-Support-Inbound-Secret: <same secret>
"""

from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.support_inbound_pipeline import process_inbound_support_email

router = APIRouter(prefix="/api/internal/support-email", tags=["Internal support email"])


def _flatten_make_style_json(raw: dict) -> dict:
    """
    Make.com sometimes POSTs {"1": {"From": "...", "Subject": "..."}, ...}.
    Merge numeric-key inner dicts so From/to/subject map into the root object.
    """
    out: dict = {}
    nested_merged: dict = {}
    for key, val in raw.items():
        if isinstance(val, dict) and str(key).isdigit():
            nested_merged.update(val)
        else:
            out[key] = val
    out.update(nested_merged)
    return out


def _verify_inbound_secret(header_secret: str | None) -> None:
    expected = (os.getenv("SUPPORT_INBOUND_WEBHOOK_SECRET") or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="SUPPORT_INBOUND_WEBHOOK_SECRET is not set on the server",
        )
    got = (header_secret or "").strip()
    if not got or len(got) != len(expected):
        raise HTTPException(status_code=403, detail="Invalid inbound webhook secret")
    if not hmac.compare_digest(got.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=403, detail="Invalid inbound webhook secret")


@router.post("/inbound")
def webhook_inbound(
    db: Session = Depends(get_db),
    x_support_inbound_secret: str | None = Header(None, alias="X-Support-Inbound-Secret"),
    from_email: str = Form(..., alias="from"),
    to: str = Form(default=""),
    subject: str = Form(default=""),
    text: str | None = Form(default=None),
    html: str | None = Form(default=None),
    headers: str | None = Form(default=None),
):
    _verify_inbound_secret(x_support_inbound_secret)
    mailbox = (os.getenv("SUPPORT_INBOUND_MAILBOX", "support@jewishcoacher.com") or "").strip()
    result = process_inbound_support_email(
        db,
        from_field=from_email,
        to_field=to or "",
        subject=subject or "",
        text_part=text,
        html_part=html,
        headers_raw=headers,
        mailbox_must_match=mailbox or None,
    )
    return result


class InboundJsonBody(BaseModel):
    """Payload for Make/Zapier HTTP modules (map IMAP fields into JSON).

    Accepts several key aliases — automation tools often rename fields (e.g. Sender vs from).
    """

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    from_: str = Field(
        default="",
        validation_alias=AliasChoices(
            "from",
            "from_email",
            "sender",
            "From",
            "Sender",
            "SenderEmail",
            "sender_email",
            "senderEmail",
            "SenderEmailAddress",
            "sender_email_address",
            "Source",
            "mail_from",
            "reply_from",
        ),
        description="RFC5322 From, e.g. Name <user@example.com>",
    )
    to: str = Field(default="", validation_alias=AliasChoices("to", "To", "recipient", "Recipient"))
    subject: str = Field(default="", validation_alias=AliasChoices("subject", "Subject", "title"))
    text: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "text",
            "plain",
            "body",
            "snippet",
            "Text",
            "PlainText",
            "content",
            "Content",
        ),
    )
    html: str | None = Field(default=None, validation_alias=AliasChoices("html", "Html", "HTML"))
    headers: str | None = Field(default=None, validation_alias=AliasChoices("headers", "Headers", "raw_headers"))
    message_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "message_id",
            "Message-ID",
            "messageId",
            "MessageId",
            "uid",
            "email_id",
        ),
        description="Optional Message-ID or unique id for deduplication",
    )

    @field_validator("from_", mode="before")
    @classmethod
    def _coerce_from(cls, v):
        if v is None:
            return ""
        if isinstance(v, list):
            for item in v:
                if item is None:
                    continue
                if isinstance(item, dict):
                    inner = cls._coerce_from(item)
                    if inner:
                        return inner
                else:
                    s = str(item).strip()
                    if s:
                        return s
            return ""
        if isinstance(v, dict):
            return str(
                v.get("emailAddress")
                or v.get("email_address")
                or v.get("EmailAddress")
                or v.get("email")
                or v.get("address")
                or v.get("text")
                or v.get("value")
                or ""
            ).strip()
        return str(v).strip()

    @field_validator("text", "html", mode="before")
    @classmethod
    def _coerce_optional_text(cls, v):
        if v is None:
            return None
        if isinstance(v, dict):
            merged = str(v.get("plain") or v.get("text") or v.get("html") or v.get("body") or "").strip()
            return merged or None
        s = str(v).strip()
        return s or None


@router.post("/inbound-json")
async def webhook_inbound_json(
    request: Request,
    db: Session = Depends(get_db),
    x_support_inbound_secret: str | None = Header(None, alias="X-Support-Inbound-Secret"),
):
    """JSON body — typical for Make.com / Zapier 'HTTP' actions after an IMAP trigger."""
    _verify_inbound_secret(x_support_inbound_secret)
    try:
        raw_body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from None
    if not isinstance(raw_body, dict):
        raise HTTPException(status_code=400, detail="JSON body must be a JSON object")

    payload = _flatten_make_style_json(raw_body)
    try:
        body = InboundJsonBody.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from None

    if not (body.from_ or "").strip():
        keys_preview = sorted(payload.keys())[:48]
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_sender",
                "hint": (
                    "Map the Email module field «Sender: Email address» or «From» into JSON key "
                    "`from`, `sender`, or `From`. If Make wraps output under `1`, merge or map from inside that object."
                ),
                "received_top_level_keys": keys_preview,
            },
        )
    mailbox = (os.getenv("SUPPORT_INBOUND_MAILBOX", "support@jewishcoacher.com") or "").strip()
    result = process_inbound_support_email(
        db,
        from_field=body.from_,
        to_field=body.to or "",
        subject=body.subject or "",
        text_part=body.text,
        html_part=body.html,
        headers_raw=body.headers,
        mailbox_must_match=mailbox or None,
        message_id_override=body.message_id,
        inbound_channel="imap_automation_json",
    )
    return result

