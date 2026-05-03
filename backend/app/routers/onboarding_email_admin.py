"""Admin API: onboarding email sequences (drip campaigns for new users)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_admin_user
from ..models import (
    OnboardingEmailSequence,
    OnboardingEmailStep,
    User,
)
from ..services.email_service import send_html_email
from ..services.onboarding_email_ai import generate_onboarding_step_draft
from ..services.onboarding_email_runtime import (
    build_final_html,
    process_due_onboarding_emails,
    public_app_url,
)

router = APIRouter(
    prefix="/api/admin/onboarding-email",
    tags=["Admin onboarding email"],
    dependencies=[Depends(get_current_admin_user)],
)


def _clear_other_defaults(db: Session, keep_id: Optional[int]) -> None:
    q = db.query(OnboardingEmailSequence).filter(OnboardingEmailSequence.is_default.is_(True))
    if keep_id is not None:
        q = q.filter(OnboardingEmailSequence.id != keep_id)
    for row in q.all():
        row.is_default = False


def _step_payload(step: OnboardingEmailStep) -> dict[str, Any]:
    urls = step.image_urls if isinstance(step.image_urls, list) else []
    return {
        "id": step.id,
        "sequence_id": step.sequence_id,
        "sort_order": step.sort_order,
        "delay_after_previous_minutes": step.delay_after_previous_minutes,
        "subject": step.subject,
        "body_html": step.body_html,
        "body_plain": step.body_plain,
        "image_urls": urls,
        "created_at": step.created_at.isoformat() if step.created_at else None,
        "updated_at": step.updated_at.isoformat() if step.updated_at else None,
    }


def _sequence_payload(seq: OnboardingEmailSequence, db: Session) -> dict[str, Any]:
    steps = (
        db.query(OnboardingEmailStep)
        .filter(OnboardingEmailStep.sequence_id == seq.id)
        .order_by(OnboardingEmailStep.sort_order.asc())
        .all()
    )
    return {
        "id": seq.id,
        "name": seq.name,
        "description": seq.description,
        "is_active": seq.is_active,
        "is_default": seq.is_default,
        "created_at": seq.created_at.isoformat() if seq.created_at else None,
        "updated_at": seq.updated_at.isoformat() if seq.updated_at else None,
        "steps": [_step_payload(s) for s in steps],
    }


class SequenceCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    is_active: bool = True
    is_default: bool = False


class SequencePatch(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class StepCreate(BaseModel):
    delay_after_previous_minutes: int = Field(0, ge=0, le=525600)
    subject: str = Field(..., max_length=500)
    body_html: str = ""
    body_plain: Optional[str] = None
    image_urls: list[str] = Field(default_factory=list)


class StepPatch(BaseModel):
    delay_after_previous_minutes: Optional[int] = Field(None, ge=0, le=525600)
    subject: Optional[str] = Field(None, max_length=500)
    body_html: Optional[str] = None
    body_plain: Optional[str] = None
    image_urls: Optional[list[str]] = None
    sort_order: Optional[int] = Field(None, ge=0)


class StepReorderBody(BaseModel):
    ordered_step_ids: list[int]


class DraftBody(BaseModel):
    admin_prompt: str = Field(..., min_length=3, max_length=8000)
    language: str = Field("he", max_length=12)
    sequence_id: Optional[int] = None
    step_id: Optional[int] = None


class PreviewBody(BaseModel):
    sample_display_name: str = Field("דוגמה", max_length=120)
    sample_email: str = Field("user@example.com", max_length=320)


class TestSendBody(BaseModel):
    step_id: int
    to_email: str = Field(..., max_length=320)


@router.get("/meta")
def onboarding_email_meta():
    """Hints for editors (placeholders, app URL)."""
    return {
        "placeholders": ["{{display_name}}", "{{email}}", "{{app_url}}"],
        "default_app_url": public_app_url(),
    }


@router.get("/sequences")
def list_sequences(db: Session = Depends(get_db)):
    rows = db.query(OnboardingEmailSequence).order_by(OnboardingEmailSequence.id.asc()).all()
    return {"sequences": [_sequence_payload(r, db) for r in rows]}


@router.post("/sequences")
def create_sequence(body: SequenceCreate, db: Session = Depends(get_db)):
    if body.is_default:
        _clear_other_defaults(db, None)
    seq = OnboardingEmailSequence(
        name=body.name.strip(),
        description=(body.description or "").strip() or None,
        is_active=body.is_active,
        is_default=body.is_default,
    )
    db.add(seq)
    db.commit()
    db.refresh(seq)
    return _sequence_payload(seq, db)


@router.get("/sequences/{sequence_id}")
def get_sequence(sequence_id: int, db: Session = Depends(get_db)):
    seq = db.query(OnboardingEmailSequence).filter(OnboardingEmailSequence.id == sequence_id).first()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return _sequence_payload(seq, db)


@router.patch("/sequences/{sequence_id}")
def patch_sequence(sequence_id: int, body: SequencePatch, db: Session = Depends(get_db)):
    seq = db.query(OnboardingEmailSequence).filter(OnboardingEmailSequence.id == sequence_id).first()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")
    if body.name is not None:
        seq.name = body.name.strip()
    if body.description is not None:
        seq.description = body.description.strip() or None
    if body.is_active is not None:
        seq.is_active = body.is_active
    if body.is_default is not None:
        if body.is_default:
            _clear_other_defaults(db, seq.id)
        seq.is_default = body.is_default
    db.commit()
    db.refresh(seq)
    return _sequence_payload(seq, db)


@router.delete("/sequences/{sequence_id}")
def delete_sequence(sequence_id: int, db: Session = Depends(get_db)):
    seq = db.query(OnboardingEmailSequence).filter(OnboardingEmailSequence.id == sequence_id).first()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")
    db.delete(seq)
    db.commit()
    return {"ok": True}


@router.post("/sequences/{sequence_id}/steps")
def create_step(sequence_id: int, body: StepCreate, db: Session = Depends(get_db)):
    seq = db.query(OnboardingEmailSequence).filter(OnboardingEmailSequence.id == sequence_id).first()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")
    mx = (
        db.query(func.coalesce(func.max(OnboardingEmailStep.sort_order), -1))
        .filter(OnboardingEmailStep.sequence_id == sequence_id)
        .scalar()
    )
    sort_order = int(mx or -1) + 1
    step = OnboardingEmailStep(
        sequence_id=sequence_id,
        sort_order=sort_order,
        delay_after_previous_minutes=int(body.delay_after_previous_minutes),
        subject=body.subject.strip(),
        body_html=body.body_html or "<p></p>",
        body_plain=body.body_plain,
        image_urls=[u.strip() for u in body.image_urls if isinstance(u, str) and u.strip()],
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return _step_payload(step)


@router.patch("/steps/{step_id}")
def patch_step(step_id: int, body: StepPatch, db: Session = Depends(get_db)):
    step = db.query(OnboardingEmailStep).filter(OnboardingEmailStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    if body.delay_after_previous_minutes is not None:
        step.delay_after_previous_minutes = int(body.delay_after_previous_minutes)
    if body.subject is not None:
        step.subject = body.subject.strip()
    if body.body_html is not None:
        step.body_html = body.body_html
    if body.body_plain is not None:
        step.body_plain = body.body_plain
    if body.image_urls is not None:
        step.image_urls = [u.strip() for u in body.image_urls if isinstance(u, str) and u.strip()]
    if body.sort_order is not None:
        step.sort_order = int(body.sort_order)
    db.commit()
    db.refresh(step)
    return _step_payload(step)


@router.delete("/steps/{step_id}")
def delete_step(step_id: int, db: Session = Depends(get_db)):
    step = db.query(OnboardingEmailStep).filter(OnboardingEmailStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    sid = step.sequence_id
    db.delete(step)
    db.commit()
    steps = (
        db.query(OnboardingEmailStep)
        .filter(OnboardingEmailStep.sequence_id == sid)
        .order_by(OnboardingEmailStep.sort_order.asc(), OnboardingEmailStep.id.asc())
        .all()
    )
    for i, s in enumerate(steps):
        s.sort_order = i
    db.commit()
    return {"ok": True}


@router.put("/sequences/{sequence_id}/steps/reorder")
def reorder_steps(sequence_id: int, body: StepReorderBody, db: Session = Depends(get_db)):
    seq = db.query(OnboardingEmailSequence).filter(OnboardingEmailSequence.id == sequence_id).first()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")
    steps = (
        db.query(OnboardingEmailStep).filter(OnboardingEmailStep.sequence_id == sequence_id).all()
    )
    by_id = {s.id: s for s in steps}
    wanted = list(body.ordered_step_ids)
    if len(wanted) != len(by_id) or set(wanted) != set(by_id.keys()):
        raise HTTPException(status_code=400, detail="ordered_step_ids must be a permutation of all step ids")
    for i, sid in enumerate(body.ordered_step_ids):
        by_id[sid].sort_order = i
    db.commit()
    return _sequence_payload(seq, db)


@router.post("/ai/draft-step")
def ai_draft_step(body: DraftBody, db: Session = Depends(get_db)):
    seq_name = None
    prev_subjects: list[str] = []
    step_pos: Optional[int] = None
    if body.sequence_id:
        seq = db.query(OnboardingEmailSequence).filter(OnboardingEmailSequence.id == body.sequence_id).first()
        if seq:
            seq_name = seq.name
            ordered = (
                db.query(OnboardingEmailStep)
                .filter(OnboardingEmailStep.sequence_id == seq.id)
                .order_by(OnboardingEmailStep.sort_order.asc())
                .all()
            )
            prev_subjects = [s.subject for s in ordered if s.subject]
            if body.step_id:
                st = next((x for x in ordered if x.id == body.step_id), None)
                if st:
                    step_pos = ordered.index(st) + 1
            elif ordered:
                step_pos = len(ordered) + 1
    try:
        out = generate_onboarding_step_draft(
            admin_prompt=body.admin_prompt,
            language=body.language,
            sequence_name=seq_name,
            step_position=step_pos,
            previous_subjects=prev_subjects or None,
        )
        return {"subject": out.subject, "body_html": out.body_html, "body_plain": out.body_plain}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"AI draft failed: {type(e).__name__}: {e}") from e


@router.post("/sequences/{sequence_id}/preview-step/{step_id}")
def preview_step(sequence_id: int, step_id: int, body: PreviewBody, db: Session = Depends(get_db)):
    step = (
        db.query(OnboardingEmailStep)
        .filter(OnboardingEmailStep.id == step_id, OnboardingEmailStep.sequence_id == sequence_id)
        .first()
    )
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    u = User(
        clerk_id="preview_user",
        email=body.sample_email.strip(),
        display_name=body.sample_display_name.strip(),
    )
    subject, html_body, plain = build_final_html(step, u)
    return {"subject": subject, "body_html": html_body, "body_plain": plain}


@router.post("/sequences/{sequence_id}/test-send")
def test_send(sequence_id: int, body: TestSendBody, db: Session = Depends(get_db)):
    step = (
        db.query(OnboardingEmailStep)
        .filter(OnboardingEmailStep.id == body.step_id, OnboardingEmailStep.sequence_id == sequence_id)
        .first()
    )
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    to_email = body.to_email.strip()
    u = User(clerk_id="admin_test_send", email=to_email, display_name="בדיקת מנהל")
    subject, html_body, plain = build_final_html(step, u)
    ok = send_html_email(to_email, subject, html_body, plain)
    return {"sent": bool(ok)}


@router.post("/process-due")
def process_due(db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=200)):
    """Send due onboarding emails (run from cron or manually)."""
    return process_due_onboarding_emails(db, limit=limit)
