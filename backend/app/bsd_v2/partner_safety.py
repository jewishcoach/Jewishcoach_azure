"""
Couple process only: signals of violence from the partner, or fear of the partner.

Same two tiers as safety_check.py, because arguments, shouting and anger are exactly what couples bring to
coaching: a regex prefilter, then a classifier (none | conflict | possible_abuse | danger). Only possible_abuse /
danger pause the process with a private check-in; the shared screens are held at once, silently — the partner
keeps seeing "waiting", nothing that hints at why.

After the check-in the next message is always classified with the check-in as context: if the user says they
are safe, the hold is released and coaching resumes; otherwise the user goes on alone (left quietly) and nothing
of theirs is ever shown to the partner.
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.bsd.llm import get_azure_chat_llm
from .safety_check import SafetyResult, _RESOURCES, _region

logger = logging.getLogger(__name__)

CLASSIFIER_TIMEOUT_SECONDS = float(os.getenv("SAFETY_CLASSIFIER_TIMEOUT_SECONDS", "8"))

# Physical violence, threats, fear, control — most messages (incl. ordinary fights) never reach the classifier.
# Final letters: הרביץ / אלים end in ץ / ם, so stems carry both forms.
_PREFILTER = re.compile(
    r"הרבי[צץ]|מרבי[צץ]|מכה אותי|הכה אותי|היכה|הכתה|סטר|סוטר|חנק|חונק|דחף אותי|דחפה אותי|בעט|זרק עליי|זרקה עליי|"
    r"איים|איימה|מאיים|מאיימת|איום|אלי[םמ]|מפחד(?:ת)? (?:ממנו|ממנה|לחזור הביתה|להיות לבד איתו|להיות לבד איתה)|"
    r"פוחד(?:ת)? ממנו|פוחד(?:ת)? ממנה|לא (?:נותן|נותנת) לי לצאת|נעל אותי|נועל אותי|לוקח לי את הטלפון|"
    r"בודק לי את הטלפון|לא (?:נותן|נותנת) לי כסף|בכוח|אונס|סכין|נשק|"
    r"hit me|hits me|beat me|slapp|chok|pushed me|threaten|afraid of (?:him|her)|scared of (?:him|her)|abus|violen",
    re.IGNORECASE,
)
_SAFE_REPLY = re.compile(r"אני בטוח|אני בטוחה|אני בסדר|הכל בסדר|הכול בסדר|זה היה ויכוח|אין אלימות|לא מפחד|i'?m safe", re.IGNORECASE)

Level = Literal["none", "conflict", "possible_abuse", "danger"]


class _PartnerOutput(BaseModel):
    level: Level = Field(description="none | conflict | possible_abuse | danger")
    user_says_safe: bool = Field(
        default=False,
        description="Only when replying to a partner-safety check-in: the user clearly says they are safe with the partner",
    )


_CLASSIFIER_PROMPT = """You screen messages from a Hebrew/English coaching chat. The person is working, alone, on a
charged moment with their spouse/partner. Arguments are ORDINARY — yelling, harsh words, anger, criticism, cold silence,
slamming a door, leaving the room, crying. Classify the LATEST user message for abuse BY THE PARTNER:

- none: no violence or fear of the partner. Figurative language is none: "הוא דחף אותי להחליט", "היא הורגת אותי עם
  הבקשות", "הוא רצח אותי במבט", "בכוח רצון", "I could kill him", "it's killing me".
- conflict: ordinary conflict between partners — shouting, insults, anger, criticism, threats to end a conversation or to
  leave the room, the client's own anger ("רציתי לזרוק משהו", "צעקתי עליו").
- possible_abuse: physical violence by the partner (hitting, pushing, choking, throwing things at the person), threats
  to hurt / to take the children / to leave them with nothing, fear of the partner, control (not letting them leave,
  taking or checking their phone, controlling all the money), forced sex.
- danger: danger right now — being hurt or threatened at this moment, a weapon, fear for their life or the children's.

If the coach just asked a partner-safety check-in, set user_says_safe=true ONLY if the user clearly says they are safe
with the partner and there is no violence or fear ("זה היה ויכוח קשה, אני מרגישה בטוחה איתו" → conflict, true).
"I don't know", hesitation, or confirming the violence → user_says_safe=false.
Return only the fields — no explanation."""


def _g(gender: Optional[str]):
    return lambda m, f: f if gender == "female" else m


def _lines(tz: Optional[str]) -> tuple[str, str]:
    emergency = _RESOURCES[_region(tz)][1]
    if _region(tz) == "IL":
        return "מוקד 118 של משרד הרווחה — אלימות במשפחה, גם בדיסקרטיות", "משטרה: 100"
    return "קו הסיוע המקומי לנפגעות ולנפגעי אלימות במשפחה", emergency


# Fixed texts (stored as coach messages) — the prefixes mark them for is_partner_safety_message
_CHECK_IN_PREFIX = "אני עוצר כאן לרגע, כי ביטחון חשוב יותר מכל תהליך."
_DANGER_PREFIX = "מה שכתבת מדאיג אותי מאוד, ואני רוצה שתהיה לך הגנה עכשיו."
_HELD_PREFIX = "תודה שסיפרת לי — זה לא פשוט לכתוב את זה."


def build_partner_check_in(tz: Optional[str], gender: Optional[str]) -> str:
    g = _g(gender)
    line, emergency = _lines(tz)
    return (
        f"{_CHECK_IN_PREFIX}\n"
        f"אני שואל ישירות: {g('אתה מרגיש בטוח', 'את מרגישה בטוחה')} עם בן/בת הזוג? יש אלימות, איומים או פחד?\n\n"
        "אם כן — החלק המשותף לא מתאים עכשיו, ושום דבר ממה שכתבת לא יוצג לבן/בת הזוג. אפשר לפנות:\n"
        f"• {line}\n• בסכנה מיידית — {emergency}\n\n"
        f"ואם זה היה ויכוח קשה ו{g('אתה מרגיש בטוח', 'את מרגישה בטוחה')} — אפשר לכתוב לי, ונמשיך מאיפה שעצרנו."
    )


def build_partner_danger(tz: Optional[str], gender: Optional[str]) -> str:
    line, emergency = _lines(tz)
    return (
        f"{_DANGER_PREFIX}\n\n"
        f"• אם יש סכנה עכשיו — {emergency}, עכשיו.\n• {line}\n\n"
        "שום דבר ממה שכתבת לא יוצג לבן/בת הזוג. אני כאן, ואפשר להמשיך לכתוב לי."
    )


def build_partner_held(tz: Optional[str], gender: Optional[str]) -> str:
    g = _g(gender)
    line, emergency = _lines(tz)
    return (
        f"{_HELD_PREFIX}\n"
        "החלק המשותף נעצר כאן: בן/בת הזוג לא יראו שום דבר ממה שכתבת, ומבחינתם זה ייראה כאילו עוד לא סיימת.\n"
        f"{g('אתה יכול', 'את יכולה')} להמשיך כאן תהליך אישי, בקצב שלך.\n\n"
        f"• {line}\n• בסכנה מיידית — {emergency}"
    )


def is_partner_safety_message(text: Optional[str]) -> bool:
    return (text or "").startswith((_CHECK_IN_PREFIX, _DANGER_PREFIX, _HELD_PREFIX))


async def _classify(message: str, last_coach: str, after_check_in: bool) -> Optional[_PartnerOutput]:
    llm = get_azure_chat_llm(purpose="safety").with_structured_output(_PartnerOutput)
    context = ("The coach just asked a partner-safety check-in: " if after_check_in else "Previous coach message: ") + last_coach[-600:]
    try:
        return await asyncio.wait_for(
            llm.ainvoke([SystemMessage(content=_CLASSIFIER_PROMPT),
                         HumanMessage(content=f"{context}\n\nLATEST user message:\n{message}")]),
            timeout=CLASSIFIER_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.exception("[PartnerSafety] classifier failed")
        return None


def _last_coach(state: dict[str, Any]) -> str:
    return next((m.get("content") or "" for m in reversed(state.get("messages") or []) if m.get("sender") == "coach"), "")


# hold actions for couple_service.apply_safety_hold
HOLD, RELEASE, LEAVE = "hold", "release", "leave"


@dataclass
class PartnerSafetyResult:
    result: SafetyResult
    hold_action: Optional[str] = None


async def screen_partner_message(message: str, state: dict[str, Any], tz: Optional[str] = None,
                                 gender: Optional[str] = None) -> PartnerSafetyResult:
    """Couple conversations only. Mutates state["partner_safety"] to track a pending check-in."""
    ps = state.setdefault("partner_safety", {})
    pending = ps.get("status") == "check_pending"
    text = message or ""
    if not pending and not _PREFILTER.search(text):
        return PartnerSafetyResult(SafetyResult(intercept=False))

    out = await _classify(text, _last_coach(state), after_check_in=pending)
    if out is None:  # classifier unavailable: a prefilter hit is enough for a check-in; a clear "safe" clears it
        out = _PartnerOutput(level="possible_abuse", user_says_safe=pending and bool(_SAFE_REPLY.search(text))
                             and not _PREFILTER.search(text))

    now = datetime.now(timezone.utc).isoformat()
    if pending and out.user_says_safe and out.level != "danger":
        ps.update(status="cleared", cleared_at=now)
        logger.info("[PartnerSafety] check-in cleared — shared part resumes")
        return PartnerSafetyResult(SafetyResult(intercept=False, level=out.level), RELEASE)
    if out.level == "danger":
        ps.update(status="check_pending", level="danger", at=now)
        logger.warning("[PartnerSafety] danger signal")
        return PartnerSafetyResult(SafetyResult(intercept=True, message=build_partner_danger(tz, gender), level="partner_danger"), HOLD)
    if pending:
        ps.update(status="held", at=now)
        logger.warning("[PartnerSafety] check-in not cleared — member goes on alone")
        return PartnerSafetyResult(SafetyResult(intercept=True, message=build_partner_held(tz, gender), level="partner_held"), LEAVE)
    if out.level == "possible_abuse":
        ps.update(status="check_pending", level="possible_abuse", at=now)
        logger.warning("[PartnerSafety] possible abuse — check-in")
        return PartnerSafetyResult(SafetyResult(intercept=True, message=build_partner_check_in(tz, gender),
                                                level="partner_check"), HOLD)
    return PartnerSafetyResult(SafetyResult(intercept=False, level=out.level))
