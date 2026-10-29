"""Couple process — one shared event, each partner in a private conversation, two shared screens.

Flow (user decisions Oct 29 2026): each partner works alone S2–S11 → both approve the lines they
share → mirror screen → each alone S12–S15 → both approve → commitment screen.

Privacy: nothing from one partner's conversation reaches the other partner or the other partner's
coach — only the lines a member approved, and only after both approved.
"""
import hashlib
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..bsd_v2.state_schema_v2 import create_initial_state
from ..database import utc_now
from ..models import Conversation, CoupleMember, CoupleSession, User

logger = logging.getLogger(__name__)

INVITE_TTL = timedelta(days=14)
TITLE_MAX = 80
NAME_MAX = 40
LINE_MAX = 300
CHECKPOINTS = ("mirror", "commitment")

# Shared-screen lines in display order; the headings live in the frontend (v3/couple/lines.ts)
MIRROR_LINE_IDS = ("emotions", "thought", "action", "desired_emotion", "desired_action",
                   "pattern", "paradigm", "stance", "trigger", "gains", "losses")
COMMITMENT_LINE_IDS = ("new_stance", "new_action", "request")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_invite_token(session: CoupleSession) -> str:
    """A fresh link token (shown once); only its hash is stored, and an older link stops working."""
    token = secrets.token_urlsafe(24)
    session.invite_token_hash = hash_token(token)
    session.invite_expires_at = utc_now() + INVITE_TTL
    return token


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    # SQLite returns naive datetimes for values written as UTC
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def invite_expired(session: CoupleSession) -> bool:
    exp = _aware(session.invite_expires_at)
    return exp is None or exp < utc_now()


def _step_num(step: Optional[str]) -> int:
    try:
        return int(str(step or "S0").lstrip("S"))
    except ValueError:
        return 0


# ── conversations ───────────────────────────────────────────────────────────────

def create_member_conversation(db: Session, user: User, session: CoupleSession, role: str) -> Conversation:
    """The member's own conversation, seeded so V3 starts at the event (S2) with the shared title as the topic."""
    conv = Conversation(user_id=user.id, title=f"תהליך זוגי — {session.event_title}"[:120])
    db.add(conv)
    db.flush()
    state = create_initial_state(conversation_id=str(conv.id), user_id=str(user.id), language="he")
    state["ux_version"] = 3
    state["couple"] = {"session_id": session.id, "role": role, "event_title": session.event_title}
    state["collected_data"]["topic"] = f"אירוע זוגי: {session.event_title}"
    conv.v2_state = state
    return conv


def member_for_user(db: Session, session_id: int, user_id: int) -> Optional[CoupleMember]:
    return db.query(CoupleMember).filter(
        CoupleMember.session_id == session_id, CoupleMember.user_id == user_id
    ).first()


def partner_of(member: CoupleMember) -> Optional[CoupleMember]:
    return next((m for m in member.session.members if m.id != member.id), None)


# ── shared screens ──────────────────────────────────────────────────────────────

def screen_open(session: CoupleSession, checkpoint: str) -> bool:
    """Open only when both partners approved their lines, nobody left, and no safety hold."""
    members = session.members
    return (
        session.status == "active"
        and len(members) == 2
        and all(getattr(m, f"{checkpoint}_at") for m in members)
        and not any(m.safety_hold_at or m.left_at for m in members)
    )


def _waits_for_mirror(member: Optional[CoupleMember]) -> bool:
    if member is None or member.left_at is not None:
        return False
    if member.session.status == "cancelled":
        return False
    return not screen_open(member.session, "mirror")


def waiting_for_mirror(db: Session, conversation_id: int) -> bool:
    """True when this conversation belongs to an ongoing couple process whose mirror screen hasn't opened."""
    member = db.query(CoupleMember).filter(CoupleMember.conversation_id == conversation_id).first()
    return _waits_for_mirror(member)


def clamp_before_mirror(db: Session, conversation_id: int, state: Dict[str, Any]) -> None:
    """Invariant on every save: a couple conversation never passes S11 before the mirror screen opened."""
    if _step_num(state.get("current_step")) < 12 or not waiting_for_mirror(db, conversation_id):
        return
    logger.warning("[Couple] conv %s reached %s before the mirror screen — held at S11",
                   conversation_id, state.get("current_step"))
    state["current_step"] = "S11"


# S8 keeps the pattern as the coach phrased it ("הדפוס שלך הוא להגיב… כשאת מרגישה… שלך"), but on the shared screen
# it sits under "הדפוס שלי". Only unambiguous second-person words — a bare "את" is also the object marker.
_SECOND_TO_FIRST = {
    "כשאת": "כשאני", "כשאתה": "כשאני", "שאתה": "שאני", "אתה": "אני", "שלך": "שלי", "אותך": "אותי", "ממך": "ממני",
    "לך": "לי", "בך": "בי", "איתך": "איתי", "אלייך": "אליי", "אליך": "אליי", "עלייך": "עליי", "עליך": "עליי",
    "כלפייך": "כלפיי", "כלפיך": "כלפיי", "בשבילך": "בשבילי", "לעצמך": "לעצמי", "בעצמך": "בעצמי",
}
_SECOND_PERSON_WORD = re.compile(
    r"(?<![\u0590-\u05FF])(" + "|".join(sorted(_SECOND_TO_FIRST, key=len, reverse=True)) + r")(?![\u0590-\u05FF])")


def _first_person(text: str) -> str:
    return _SECOND_PERSON_WORD.sub(lambda m: _SECOND_TO_FIRST[m.group(1)], text)


def _text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(v).strip() for v in value if str(v).strip())
    return " ".join(str(value or "").split())


def mirror_ready(state: Dict[str, Any]) -> bool:
    """Discovery is done: the S11 balance was filled."""
    stance = (state.get("collected_data") or {}).get("stance") or {}
    return _step_num(state.get("current_step")) >= 11 and bool(stance.get("gains") or stance.get("losses"))


def commitment_ready(state: Dict[str, Any]) -> bool:
    cd = state.get("collected_data") or {}
    return _step_num(state.get("current_step")) >= 15 and bool(cd.get("commitment"))


def mirror_draft(state: Dict[str, Any]) -> List[Dict[str, str]]:
    """The member's own words from the conversation, one line per heading (empty ones skipped)."""
    from ..bsd_v2.single_agent_coach import _S4_NO_THOUGHT
    cd = state.get("collected_data") or {}
    stance = cd.get("stance") or {}
    thought = _text(cd.get("thought"))
    values = {
        "emotions": _text(cd.get("emotions")),
        "thought": "" if thought == _S4_NO_THOUGHT else thought,
        "action": _text(cd.get("action_actual")),
        "desired_emotion": _text(cd.get("emotion_desired")),
        "desired_action": _text(cd.get("action_desired")),
        "pattern": _first_person(_text(cd.get("pattern"))),
        "paradigm": _text(cd.get("paradigm")),
        "stance": _text(stance.get("short") or stance.get("reality_belief")),
        "trigger": _text(stance.get("activation_trigger")),
        "gains": _text(stance.get("gains")),
        "losses": _text(stance.get("losses")),
    }
    return [{"id": k, "text": values[k][:LINE_MAX]} for k in MIRROR_LINE_IDS if values[k]]


def commitment_draft(state: Dict[str, Any]) -> List[Dict[str, str]]:
    cd = state.get("collected_data") or {}
    values = {
        "new_stance": _text(cd.get("renewal_belief")),
        "new_action": _text(cd.get("new_action")),
        "request": _text(cd.get("commitment")),
    }
    return [{"id": k, "text": values[k][:LINE_MAX * 2]} for k in COMMITMENT_LINE_IDS if values[k]]


def approved_lines(submitted: List[Dict[str, Any]], draft: List[Dict[str, str]], max_len: int) -> List[Dict[str, str]]:
    """Keep only draft line ids the member left visible, with their (possibly edited) text, in draft order."""
    by_id: Dict[str, Dict[str, Any]] = {}
    for line in submitted:
        if isinstance(line, dict) and isinstance(line.get("id"), str):
            by_id.setdefault(line["id"], line)
    out = []
    for d in draft:
        line = by_id.get(d["id"])
        if line is None or line.get("visible") is False:
            continue
        text = " ".join(str(line.get("text") if line.get("text") is not None else d["text"]).split())[:max_len]
        if text:
            out.append({"id": d["id"], "text": text})
    return out


# ── status for one member (no content, no step-level progress) ──────────────────

def status_for(member: CoupleMember) -> Dict[str, Any]:
    session = member.session
    partner = partner_of(member)
    # A partner under a safety hold (or who left after one) looks exactly like one who hasn't finished yet
    partner_hidden = bool(partner and (partner.safety_hold_at or partner.left_at))
    return {
        "session_id": session.id,
        "event_title": session.event_title,
        "status": session.status,
        "role": member.role,
        "conversation_id": member.conversation_id,
        "me": {
            "name": member.display_name,
            "gender": member.gender,
            "mirror_done": member.mirror_at is not None,
            "commitment_done": member.commitment_at is not None,
            "left": member.left_at is not None,
        },
        "partner": None if partner is None else {
            "name": partner.display_name,
            "gender": partner.gender,
            "mirror_done": partner.mirror_at is not None and not partner_hidden,
            "commitment_done": partner.commitment_at is not None and not partner_hidden,
        },
        "mirror_open": screen_open(session, "mirror"),
        "commitment_open": screen_open(session, "commitment"),
        "mirror_seen": member.mirror_seen_at is not None,
        "commitment_seen": member.commitment_seen_at is not None,
        "invite_expired": session.status == "invited" and invite_expired(session),
    }


def shared_screen(member: CoupleMember, checkpoint: str) -> Dict[str, Any]:
    partner = partner_of(member)

    def side(m: CoupleMember) -> Dict[str, Any]:
        return {"name": m.display_name, "gender": m.gender, "lines": getattr(m, checkpoint) or []}

    return {"event_title": member.session.event_title, "me": side(member), "partner": side(partner)}


# ── ending ──────────────────────────────────────────────────────────────────────

def cancel(session: CoupleSession) -> None:
    if session.status != "cancelled":
        session.status = "cancelled"
        session.cancelled_at = utc_now()
        session.invite_token_hash = None


def on_conversation_deleted(db: Session, conversation_id: int) -> None:
    """Deleting a couple conversation ends the process and removes what that member shared."""
    member = db.query(CoupleMember).filter(CoupleMember.conversation_id == conversation_id).first()
    if member is None:
        return
    cancel(member.session)
    member.mirror = None
    member.commitment = None
    member.conversation_id = None


def apply_safety_hold(db: Session, conversation_id: int, action: Optional[str]) -> None:
    """A partner-safety signal in this member's conversation (bsd_v2/partner_safety.py): hold / release / leave quietly."""
    if not action:
        return
    member = db.query(CoupleMember).filter(CoupleMember.conversation_id == conversation_id).first()
    if member is None:
        return
    now = utc_now()
    if action == "release":
        member.safety_hold_at = None
        member.left_at = None
    else:
        member.safety_hold_at = member.safety_hold_at or now
        if action == "leave":
            member.left_at = member.left_at or now
    logger.warning("[Couple] session %s: safety %s (%s)", member.session_id, action, member.role)
