"""
Couple process endpoints — create a shared event, invite by link, approve lines, open the shared screens.
Logic and the privacy rules: services/couple_service.py.
"""
import logging
import os
from typing import List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db, utc_now
from ..dependencies import get_current_user
from ..limiter import limiter
from ..models import Conversation, CoupleMember, CoupleSession, User
from ..services import couple_notifications as notify
from ..services import couple_service as cs
from .tools import _is_gibberish

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/couple", tags=["couple"])

Checkpoint = Literal["mirror", "commitment"]


class StartRequest(BaseModel):
    event_title: str = Field(..., max_length=300)
    display_name: str = Field(..., max_length=100)
    gender: Optional[Literal["male", "female"]] = None


class JoinRequest(BaseModel):
    display_name: str = Field(..., max_length=100)
    gender: Optional[Literal["male", "female"]] = None


class ShareLine(BaseModel):
    id: str = Field(..., max_length=40)
    text: Optional[str] = Field(default=None, max_length=1000)
    visible: bool = True


class ApproveRequest(BaseModel):
    lines: List[ShareLine] = Field(default_factory=list, max_length=20)


def can_open_process(user: User) -> bool:
    """Pilot: opening a process is limited to COUPLE_PILOT_EMAILS ("*" = everyone) and admins; joining by link is open."""
    allowed = os.getenv("COUPLE_PILOT_EMAILS", "").strip()
    if allowed == "*" or user.is_admin:
        return True
    emails = {e.strip().lower() for e in allowed.split(",") if e.strip()}
    return (user.email or "").strip().lower() in emails


def _clean(text: str, max_len: int) -> str:
    return " ".join((text or "").split())[:max_len]


def _member_details(body, user: User) -> tuple[str, Optional[str]]:
    name = _clean(body.display_name, cs.NAME_MAX)
    if not name:
        raise HTTPException(status_code=422, detail={"error": "display_name", "message": "מה השם שיופיע לבן/בת הזוג?"})
    if body.gender and not user.gender:
        user.gender = body.gender  # the coach and the cards read the profile gender
    return name, body.gender or user.gender


def _member_or_404(db: Session, session_id: int, user: User) -> CoupleMember:
    member = cs.member_for_user(db, session_id, user.id)
    if member is None:
        raise HTTPException(status_code=404, detail="Not found")
    return member


def _session_by_token(db: Session, token: str) -> CoupleSession:
    session = db.query(CoupleSession).filter(CoupleSession.invite_token_hash == cs.hash_token(token)).first()
    if session is None:
        raise HTTPException(status_code=404, detail={"code": "invite_not_found"})
    return session


@router.get("/enabled")
def couple_enabled(user: User = Depends(get_current_user)):
    return {"can_start": can_open_process(user)}


@router.post("/sessions")
@limiter.limit("10/minute")
def start_session(
    request: Request,
    body: StartRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Partner A opens a shared event: their own conversation + a one-time invite link token."""
    if not can_open_process(user):
        raise HTTPException(status_code=404, detail="Not found")
    title = _clean(body.event_title, cs.TITLE_MAX)
    if len(title) < 2 or _is_gibberish(title):
        raise HTTPException(status_code=422, detail={"error": "event_title", "message": "כותרת קצרה: מתי ועל מה"})
    name, gender = _member_details(body, user)

    session = CoupleSession(event_title=title, status="invited")
    db.add(session)
    db.flush()
    token = cs.new_invite_token(session)
    conv = cs.create_member_conversation(db, user, session, "inviter")
    db.add(CoupleMember(session_id=session.id, user_id=user.id, conversation_id=conv.id,
                        role="inviter", display_name=name, gender=gender))
    db.commit()
    logger.info("[Couple] session %s opened (conv %s)", session.id, conv.id)
    return {"session_id": session.id, "conversation_id": conv.id, "invite_token": token}


@router.post("/sessions/{session_id}/invite")
@limiter.limit("10/minute")
def renew_invite(
    request: Request,
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """A new link for the inviter (lost or expired); the previous link stops working."""
    member = _member_or_404(db, session_id, user)
    if member.role != "inviter" or member.session.status != "invited":
        raise HTTPException(status_code=409, detail={"code": "no_invite"})
    token = cs.new_invite_token(member.session)
    db.commit()
    return {"invite_token": token}


@router.post("/sessions/{session_id}/cancel")
def cancel_session(session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Either partner can end the shared part at any time; each conversation goes on as a personal process."""
    member = _member_or_404(db, session_id, user)
    cs.cancel(member.session)
    db.commit()
    logger.info("[Couple] session %s cancelled by %s", session_id, member.role)
    return cs.status_for(member)


@router.get("/invites/{token}")
@limiter.limit("30/minute")
def get_invite(
    request: Request,
    token: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """What the invited partner sees before accepting: the inviter's name and the shared title — nothing else."""
    session = _session_by_token(db, token)
    inviter = next((m for m in session.members if m.role == "inviter"), None)
    mine = cs.member_for_user(db, session.id, user.id)
    if mine is not None and mine.role == "inviter":
        return {"state": "own", "session_id": session.id}
    if mine is not None:
        return {"state": "joined", "session_id": session.id, "conversation_id": mine.conversation_id}
    if session.status != "invited":
        return {"state": "used"}
    if cs.invite_expired(session):
        return {"state": "expired"}
    return {
        "state": "valid",
        "inviter_name": inviter.display_name if inviter else "",
        "inviter_gender": inviter.gender if inviter else None,
        "event_title": session.event_title,
    }


@router.post("/invites/{token}/accept")
@limiter.limit("10/minute")
def accept_invite(
    request: Request,
    token: str,
    body: JoinRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _session_by_token(db, token)
    if any(m.user_id == user.id for m in session.members):
        raise HTTPException(status_code=409, detail={"code": "own_or_joined"})
    if session.status != "invited":
        raise HTTPException(status_code=409, detail={"code": "used"})
    if cs.invite_expired(session):
        raise HTTPException(status_code=410, detail={"code": "expired"})
    name, gender = _member_details(body, user)
    conv = cs.create_member_conversation(db, user, session, "invitee")
    db.add(CoupleMember(session_id=session.id, user_id=user.id, conversation_id=conv.id,
                        role="invitee", display_name=name, gender=gender))
    session.status = "active"
    try:
        db.commit()
    except IntegrityError:  # a second accept raced this one
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "used"})
    logger.info("[Couple] session %s joined (conv %s)", session.id, conv.id)
    inviter = next((m for m in session.members if m.role == "inviter"), None)
    inviter_user = db.get(User, inviter.user_id) if inviter else None
    if inviter_user:
        background_tasks.add_task(notify.send_partner_joined, notify.recipient(inviter_user), name, gender)
    return {"session_id": session.id, "conversation_id": conv.id}


@router.get("/sessions")
def list_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    members = db.query(CoupleMember).filter(CoupleMember.user_id == user.id).order_by(CoupleMember.id.desc()).all()
    return [cs.status_for(m) for m in members]


@router.get("/sessions/{session_id}")
def get_status(session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return cs.status_for(_member_or_404(db, session_id, user))


def _member_state(db: Session, member: CoupleMember) -> dict:
    conv = db.get(Conversation, member.conversation_id) if member.conversation_id else None
    return (conv.v2_state if conv else None) or {}


def _draft(checkpoint: str, state: dict) -> list:
    ready = cs.mirror_ready(state) if checkpoint == "mirror" else cs.commitment_ready(state)
    if not ready:
        raise HTTPException(status_code=409, detail={"code": "not_ready"})
    return cs.mirror_draft(state) if checkpoint == "mirror" else cs.commitment_draft(state)


@router.get("/sessions/{session_id}/{checkpoint}/draft")
def get_draft(
    session_id: int,
    checkpoint: Checkpoint,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The member's own lines for the preview, plus what they approved before (to edit again)."""
    member = _member_or_404(db, session_id, user)
    if member.session.status == "cancelled":
        raise HTTPException(status_code=409, detail={"code": "cancelled"})
    return {
        "lines": _draft(checkpoint, _member_state(db, member)),
        "approved": getattr(member, checkpoint),
        "locked": cs.screen_open(member.session, checkpoint),
    }


@router.post("/sessions/{session_id}/{checkpoint}")
@limiter.limit("20/minute")
def approve(
    request: Request,
    session_id: int,
    checkpoint: Checkpoint,
    body: ApproveRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Store exactly the lines the member approved; the shared screen opens once both partners approved."""
    member = _member_or_404(db, session_id, user)
    session = member.session
    if session.status == "cancelled" or member.left_at:
        raise HTTPException(status_code=409, detail={"code": "cancelled"})
    if cs.screen_open(session, checkpoint):
        raise HTTPException(status_code=409, detail={"code": "locked"})
    draft = _draft(checkpoint, _member_state(db, member))
    max_len = cs.LINE_MAX if checkpoint == "mirror" else cs.LINE_MAX * 2
    lines = cs.approved_lines([line.model_dump() for line in body.lines], draft, max_len)
    original = {d["id"]: d["text"] for d in draft}
    for line in lines:
        if line["text"] != original.get(line["id"]) and _is_gibberish(line["text"]):
            raise HTTPException(status_code=422, detail={"error": "gibberish", "field": line["id"],
                                                         "message": "השורה לא ברורה — נסה לנסח אחרת"})
    setattr(member, checkpoint, lines)
    setattr(member, f"{checkpoint}_at", utc_now())
    db.commit()
    opened = cs.screen_open(session, checkpoint)
    logger.info("[Couple] session %s: %s approved %s (%d lines), open=%s", session.id, member.role,
                checkpoint, len(lines), opened)
    partner = cs.partner_of(member)
    partner_user = db.get(User, partner.user_id) if opened and partner else None
    if partner_user:  # the partner finished first and is waiting
        background_tasks.add_task(notify.send_screen_open, notify.recipient(partner_user),
                                  member.display_name, member.gender, checkpoint)
    return cs.status_for(member)


@router.get("/sessions/{session_id}/{checkpoint}")
def get_shared_screen(
    session_id: int,
    checkpoint: Checkpoint,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = _member_or_404(db, session_id, user)
    if not cs.screen_open(member.session, checkpoint):
        raise HTTPException(status_code=409, detail={"code": "not_open"})
    if getattr(member, f"{checkpoint}_seen_at") is None:
        setattr(member, f"{checkpoint}_seen_at", utc_now())
        db.commit()
    return cs.shared_screen(member, checkpoint)
