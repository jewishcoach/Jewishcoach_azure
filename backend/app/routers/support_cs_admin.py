"""Admin API: customer-support assistant settings, AI drafts, and email audit trail."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_admin_user
from ..models import SupportCustomerServiceSettings, SupportEmailLog, User
from ..services.support_customer_context import build_customer_support_snapshot
from ..services.support_reply_ai import generate_support_reply_draft

router = APIRouter(
    prefix="/support-service",
    tags=["Admin customer support"],
    dependencies=[Depends(get_current_admin_user)],
)

_SETTINGS_ID = 1


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _get_or_create_settings(db: Session) -> SupportCustomerServiceSettings:
    row = db.query(SupportCustomerServiceSettings).filter(SupportCustomerServiceSettings.id == _SETTINGS_ID).first()
    if row:
        return row
    row = SupportCustomerServiceSettings(id=_SETTINGS_ID)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _settings_payload(row: SupportCustomerServiceSettings) -> dict[str, Any]:
    return {
        "personality_text": row.personality_text or "",
        "terms_and_boundaries_text": row.terms_and_boundaries_text or "",
        "methodology_context_text": row.methodology_context_text or "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class SupportSettingsPatch(BaseModel):
    personality_text: Optional[str] = None
    terms_and_boundaries_text: Optional[str] = None
    methodology_context_text: Optional[str] = None


class DraftReplyBody(BaseModel):
    customer_email: str = Field(..., min_length=3, max_length=320)
    incoming_message: str = Field(..., min_length=1, max_length=50_000)
    language: str = Field(default="he", max_length=8)
    record_inbound: bool = True
    record_draft: bool = True


class ManualLogBody(BaseModel):
    customer_email: str = Field(..., min_length=3, max_length=320)
    subject: Optional[str] = Field(None, max_length=500)
    body: str = Field(..., min_length=1, max_length=100_000)


def _resolve_user_id_for_email(db: Session, customer_email: str) -> Optional[int]:
    norm = _normalize_email(customer_email)
    if not norm or "@" not in norm:
        return None
    u = db.query(User.id).filter(User.email.isnot(None)).filter(User.email == norm).first()
    if u:
        return int(u[0])
    u2 = db.query(User.id).filter(func.lower(User.email) == norm).first()
    return int(u2[0]) if u2 else None


def _append_log(
    db: Session,
    *,
    customer_email: str,
    direction: str,
    channel: str,
    subject: Optional[str],
    body: str,
    meta: Optional[dict] = None,
) -> SupportEmailLog:
    norm = _normalize_email(customer_email)
    uid = _resolve_user_id_for_email(db, norm)
    row = SupportEmailLog(
        user_id=uid,
        customer_email=norm,
        direction=direction,
        channel=channel,
        subject=(subject or "").strip() or None,
        body=body,
        meta=meta or {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _log_row_payload(row: SupportEmailLog, display_name: Optional[str]) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "user_display_name": display_name,
        "customer_email": row.customer_email,
        "direction": row.direction,
        "channel": row.channel,
        "subject": row.subject,
        "body": row.body,
        "meta": row.meta if isinstance(row.meta, dict) else {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/settings")
async def get_support_settings(db: Session = Depends(get_db)):
    row = _get_or_create_settings(db)
    return _settings_payload(row)


@router.patch("/settings")
async def patch_support_settings(body: SupportSettingsPatch, db: Session = Depends(get_db)):
    row = _get_or_create_settings(db)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _settings_payload(row)


@router.post("/draft-reply")
async def draft_support_reply(body: DraftReplyBody, db: Session = Depends(get_db)):
    norm = _normalize_email(body.customer_email)
    if "@" not in norm:
        raise HTTPException(status_code=400, detail="Invalid customer_email")

    snapshot = build_customer_support_snapshot(db, norm)
    settings = _get_or_create_settings(db)

    if body.record_inbound and body.incoming_message.strip():
        _append_log(
            db,
            customer_email=norm,
            direction="inbound",
            channel="manual_admin",
            subject=None,
            body=body.incoming_message.strip(),
            meta={"source": "admin_draft_flow"},
        )

    try:
        draft = generate_support_reply_draft(
            customer_snapshot=snapshot,
            incoming_message=body.incoming_message,
            personality_text=settings.personality_text,
            terms_text=settings.terms_and_boundaries_text,
            methodology_text=settings.methodology_context_text,
            language=body.language,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e!s}") from e

    draft_row_id: Optional[int] = None
    if body.record_draft:
        row = _append_log(
            db,
            customer_email=norm,
            direction="draft",
            channel="ai_draft",
            subject=draft.subject.strip() or None,
            body=draft.body_plain.strip(),
            meta={"internal_notes": draft.internal_notes} if draft.internal_notes else {},
        )
        draft_row_id = row.id

    return {
        "customer_snapshot": snapshot,
        "draft": draft.model_dump(),
        "draft_log_id": draft_row_id,
    }


@router.post("/logs/inbound")
async def log_inbound_email(body: ManualLogBody, db: Session = Depends(get_db)):
    row = _append_log(
        db,
        customer_email=body.customer_email,
        direction="inbound",
        channel="manual_admin",
        subject=body.subject,
        body=body.body.strip(),
        meta={"source": "manual_only"},
    )
    dn = db.query(User.display_name).filter(User.id == row.user_id).scalar() if row.user_id else None
    return {"log": _log_row_payload(row, dn)}


@router.post("/logs/outbound")
async def log_outbound_email(body: ManualLogBody, db: Session = Depends(get_db)):
    row = _append_log(
        db,
        customer_email=body.customer_email,
        direction="outbound",
        channel="manual_admin",
        subject=body.subject,
        body=body.body.strip(),
        meta={"source": "manual_sent"},
    )
    dn = db.query(User.display_name).filter(User.id == row.user_id).scalar() if row.user_id else None
    return {"log": _log_row_payload(row, dn)}


@router.get("/logs")
async def list_support_logs(
    db: Session = Depends(get_db),
    user_id: Optional[int] = Query(None),
    customer_email: Optional[str] = Query(None, max_length=320),
    direction: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    q = db.query(SupportEmailLog).order_by(SupportEmailLog.created_at.desc())
    if user_id is not None:
        q = q.filter(SupportEmailLog.user_id == user_id)
    if customer_email:
        q = q.filter(SupportEmailLog.customer_email == _normalize_email(customer_email))
    if direction:
        d = direction.strip().lower()
        if d not in ("inbound", "outbound", "draft"):
            raise HTTPException(status_code=400, detail="direction must be inbound|outbound|draft")
        q = q.filter(SupportEmailLog.direction == d)

    total = q.count()
    rows = q.offset(skip).limit(limit).all()
    ids = [r.user_id for r in rows if r.user_id]
    names: dict[int, Optional[str]] = {}
    if ids:
        for uid, dn in db.query(User.id, User.display_name).filter(User.id.in_(ids)).all():
            names[int(uid)] = dn

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "logs": [_log_row_payload(r, names.get(r.user_id)) for r in rows],
    }


@router.get("/users/{user_id}/logs")
async def list_support_logs_for_user(user_id: int, db: Session = Depends(get_db), skip: int = 0, limit: int = 200):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    q = (
        db.query(SupportEmailLog)
        .filter(SupportEmailLog.user_id == user_id)
        .order_by(SupportEmailLog.created_at.desc())
    )
    total = q.count()
    rows = q.offset(skip).limit(min(limit, 500)).all()
    dn = u.display_name
    return {
        "user_id": user_id,
        "user_email": u.email,
        "user_display_name": dn,
        "total": total,
        "skip": skip,
        "limit": limit,
        "logs": [_log_row_payload(r, dn) for r in rows],
    }
