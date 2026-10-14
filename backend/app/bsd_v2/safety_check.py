"""
Risk screening of user messages (self-harm / suicidality), independent of the coach LLM.

Two tiers, so that venting doesn't derail coaching:
1. Regex prefilter — most messages never reach the classifier.
2. Classifier (gpt-4o, structured) on prefilter hits: none | distress | possible_risk | imminent.
   Only possible_risk / imminent pause the process with a check-in; distress continues coaching.

After a check-in the next message is always classified, with the check-in as context: if the user
says they're safe, coaching resumes in the same conversation; otherwise help resources are repeated
and the process stays paused.

Help lines are chosen by the browser time zone (X-User-Timezone header); Israel is the default.
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.bsd.llm import get_azure_chat_llm

logger = logging.getLogger(__name__)

CLASSIFIER_TIMEOUT_SECONDS = float(os.getenv("SAFETY_CLASSIFIER_TIMEOUT_SECONDS", "8"))

# Explicit wording — if the classifier is unavailable, these alone justify a check-in.
_STRONG = re.compile(
    r"להתאבד|התאבדות|אובדנ|לפגוע בעצמי|פגיעה עצמית|לשים קץ|לגמור עם (?:החיים|עצמי)|"
    r"לא רוצה לחיות|לא רוצה להיות בחיים|אין לי (?:בשביל מה|טעם) לחיות|"
    r"עדיף (?:ש)?(?:פשוט )?(?:לא אהיה|אמות|שאני לא אהיה)|עדיף בלעדיי|כולם ירוויחו אם|"
    r"suicid|kill myself|end my life|don'?t want to (?:live|be alive)|better off dead|hurt myself|self[- ]harm",
    re.IGNORECASE,
)
# Ambiguous wording (often idioms: "בא לי למות מבושה") — only the classifier decides.
_WEAK = re.compile(
    r"למות|לא (?:אהיה|להיות) (?:פה|כאן)|להיעלם|לגמור עם (?:הכל|זה)|לסיים עם הכל|אין טעם|"
    r"לא יכול(?:ה)? יותר|כדורים|לקפוץ מ|לחתוך|לא להתעורר|להירדם לתמיד|לא להיות קיימ|"
    r"want to die|disappear|can'?t go on|no point|not wake up|not (?:be )?alive",
    re.IGNORECASE,
)

_SAFE_REPLY = re.compile(
    r"אני בסדר|הכל בסדר|הכול בסדר|אני לא אעשה|לא אעשה (?:כלום|שום)|אין לי מחשבות|לא מתכוו|סתם (?:אמרתי|ביטוי)|"
    r"i'?m (?:ok|okay|fine|safe)|not going to",
    re.IGNORECASE,
)

Level = Literal["none", "distress", "possible_risk", "imminent"]


class _ClassifierOutput(BaseModel):
    level: Level = Field(description="none | distress | possible_risk | imminent")
    user_says_safe: bool = Field(
        default=False,
        description="Only when replying to a safety check-in: the user clearly says they are safe / won't harm themselves",
    )


class RiskAssessment(BaseModel):
    level: Level = Field(description="none | distress | possible_risk | imminent")
    user_says_safe: bool = Field(
        default=False,
        description="Only when replying to a safety check-in: the user clearly says they are safe / won't harm themselves",
    )
    # No free-text reason: Azure's output filter fires on explanations that mention self-harm
    reason: str = Field(default="", exclude=True)


_CLASSIFIER_PROMPT = """You screen messages from a Hebrew/English personal-coaching chat for risk of self-harm or suicide.
People often vent strong emotions in coaching — that is NOT risk. Classify the LATEST user message:

- none: no self-harm content. Idioms and hyperbole are none/distress: "בא לי למות מבושה", "אני מת מעייפות",
  "הוא יהרוג אותי", "נמאס לי מהכל", "אני גמור", "I could kill him", "this is killing me".
- In coaching, users describe their PATTERN and inner rules in social terms — these are none/distress:
  "להיעלם" / "להיות שקוף" (withdraw, go invisible: "ככה זה אצלי — עדיף לשתוק ולהיעלם"), "לבלוע" (swallow
  feelings), "לגמור עם זה" about a situation ("בא לי לגמור עם זה ולעזוב את העבודה"), and wanting to
  disappear/escape FROM A MOMENT ("פשוט רציתי להיעלם", "רציתי לברוח מהכל" after a fight). Only the wish to stop
  EXISTING / LIVING counts as risk ("להיעלם לתמיד", "שלא אהיה").
- distress: strong emotional pain, hopelessness about a situation, feeling stuck/empty/worthless — but no wish
  to die or harm oneself. ("אני כישלון", "אין טעם לנסות", "אני לא יכולה יותר עם המצב הזה")
- possible_risk: any expressed wish to die, not exist, or harm oneself, even passive or vague
  ("עדיף שלא אהיה פה", "לפעמים אני חושב שעדיף בלעדיי", "אין לי בשביל מה לחיות",
  "בא לי להירדם ולא להתעורר", "I don't want to be alive").
- imminent: plan, means, timing, or intent ("אני מחזיקה כדורים", "הלילה אני גומר עם זה", "כתבתי מכתב פרידה").

If the coach just asked a safety check-in, also set user_says_safe=true ONLY if the user clearly says they are
safe / have no intent ("אני לא אעשה כלום, אני פשוט עייפה" → user_says_safe=true, level=distress).
"I don't know", silence-like answers, or confirming thoughts → user_says_safe=false.
Passive death wishes are ALWAYS possible_risk, even when phrased as tiredness: wishing to fall asleep and not
wake up ("בא לי להירדם ולא להתעורר"), wishing not to exist, wishing life would end.
When in doubt between distress and possible_risk for an explicit wish not to exist, choose possible_risk.
Return only the fields — no explanation."""


@dataclass
class SafetyResult:
    intercept: bool
    message: str = ""
    level: str = "none"


# ── help resources ────────────────────────────────────────────────────────────

_RESOURCES = {
    "IL": ("ער״ן — עזרה ראשונה נפשית, 24/7: 1201 (או בצ'אט באתר ער״ן)", "מד״א: 101"),
    "US": ("988 — קו החירום הלאומי לבריאות הנפש (שיחה או SMS)", "911"),
    "CA": ("988 — קו החירום הלאומי לבריאות הנפש (שיחה או SMS)", "911"),
    "UK": ("NHS: 111 (לבחור באפשרות של בריאות הנפש)", "999"),
    "FR": ("3114 — הקו הלאומי למניעת אובדנות", "112"),
    "AU": ("Lifeline: 13 11 14", "000"),
    "EU": ("קו החירום המקומי", "112"),
    "OTHER": ("קו החירום המקומי לבריאות הנפש", "מספר החירום המקומי"),
}
_US_ZONES = ("America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "America/Phoenix",
             "America/Anchorage", "America/Detroit", "Pacific/Honolulu")
_CA_ZONES = ("America/Toronto", "America/Vancouver", "America/Montreal", "America/Edmonton", "America/Winnipeg",
             "America/Halifax", "America/Regina", "America/St_Johns")


def _region(tz: str | None) -> str:
    tz = (tz or "").strip()
    if not tz or tz in ("Asia/Jerusalem", "Asia/Tel_Aviv"):
        return "IL"
    if tz in _US_ZONES or tz.startswith("America/Indiana") or tz.startswith("America/Kentucky"):
        return "US"
    if tz in _CA_ZONES:
        return "CA"
    if tz in ("Europe/London", "Europe/Belfast"):
        return "UK"
    if tz == "Europe/Paris":
        return "FR"
    if tz.startswith("Australia/"):
        return "AU"
    if tz.startswith("Europe/"):
        return "EU"
    return "OTHER"


def _resources_text(tz: str | None) -> tuple[str, str]:
    line, emergency = _RESOURCES[_region(tz)]
    return line, emergency


def build_check_in_message(tz: str | None) -> str:
    line, emergency = _resources_text(tz)
    return (
        "אני עוצר כאן לרגע, כי מה שכתבת חשוב לי יותר מכל תהליך.\n"
        "אני שואל ישירות, כי זה חשוב: יש לך מחשבות לפגוע בעצמך?\n\n"
        "אם כן, או אם עכשיו זה פשוט כבד מדי — אין צורך להתמודד עם זה לבד. "
        f"אפשר לדבר עכשיו עם מישהו:\n• {line}\n• בסכנה מיידית — {emergency}\n\n"
        "ואם זו הייתה דרך לבטא כמה קשה עכשיו, והכול בסדר מבחינת הבטיחות — אפשר לכתוב לי, ונמשיך מאיפה שעצרנו."
    )


def build_imminent_message(tz: str | None) -> str:
    line, emergency = _resources_text(tz)
    return (
        "מה שכתבת מדאיג אותי מאוד, ואני רוצה שתהיה לך עזרה עכשיו.\n\n"
        f"• אם יש סכנה מיידית — {emergency}, עכשיו.\n"
        f"• {line} — יש שם אנשים שזמינים עכשיו ויודעים לעזור ברגעים כאלה.\n"
        "• אם יש מישהו קרוב — אפשר לבקש ממנו להיות לידך עכשיו.\n\n"
        "אני כאן, ואפשר להמשיך לכתוב לי."
    )


def build_still_at_risk_message(tz: str | None) -> str:
    line, emergency = _resources_text(tz)
    return (
        "תודה שסיפרת לי — זה לא פשוט לכתוב את זה.\n"
        "אני לא ממשיך כרגע בתהליך, כי הכי חשוב עכשיו זה שיהיה מישהו איתך בזה.\n\n"
        f"• {line}\n• בסכנה מיידית — {emergency}\n\n"
        "אני כאן. כשיהיה לך נכון, ואם הכול בסדר מבחינת הבטיחות — אפשר לכתוב לי ונמשיך."
    )


def is_safety_message(text: str | None) -> bool:
    """True for the fixed safety responses above (they are stored as regular coach messages)."""
    return (text or "").startswith(("אני עוצר כאן לרגע", "מה שכתבת מדאיג אותי מאוד", "תודה שסיפרת לי — זה לא פשוט"))


# ── classification ────────────────────────────────────────────────────────────

async def _classify(message: str, last_coach: str, after_check_in: bool) -> RiskAssessment | None:
    # Full gpt-4o (not mini): runs only on prefilter hits, and mini was unstable on venting vs. risk
    llm = get_azure_chat_llm(purpose="safety").with_structured_output(_ClassifierOutput)
    context = ("The coach just asked a safety check-in: " if after_check_in else "Previous coach message: ") + last_coach[-600:]
    try:
        out = await asyncio.wait_for(
            llm.ainvoke([SystemMessage(content=_CLASSIFIER_PROMPT),
                         HumanMessage(content=f"{context}\n\nLATEST user message:\n{message}")]),
            timeout=CLASSIFIER_TIMEOUT_SECONDS,
        )
        return RiskAssessment(level=out.level, user_says_safe=out.user_says_safe, reason="classifier")
    except Exception as e:
        # Azure's own content filter may refuse the classifier call — if it flagged self-harm, that IS the signal
        cf = ((getattr(e, "body", None) or {}).get("innererror") or {}).get("content_filter_result") or {}
        self_harm = cf.get("self_harm") or {}
        if self_harm.get("filtered"):
            return RiskAssessment(level="possible_risk", reason=f"azure self_harm filter ({self_harm.get('severity')})")
        logger.exception("[Safety] classifier failed")
        return None


def _last_coach(state: dict[str, Any]) -> str:
    return next((m.get("content") or "" for m in reversed(state.get("messages") or []) if m.get("sender") == "coach"), "")


async def screen_message(message: str, state: dict[str, Any], tz: str | None = None) -> SafetyResult:
    """Decide whether this user message must be answered by a safety response instead of the coach.
    Mutates state["safety"] to track a pending check-in."""
    safety = state.setdefault("safety", {})
    pending = safety.get("status") == "check_pending"
    text = message or ""

    if not pending and not (_STRONG.search(text) or _WEAK.search(text)):
        return SafetyResult(intercept=False)

    assessment = await _classify(text, _last_coach(state), after_check_in=pending)
    if assessment is None:  # classifier unavailable → fall back to the explicit patterns
        if pending:
            says_safe = bool(_SAFE_REPLY.search(text)) and not _STRONG.search(text)
            assessment = RiskAssessment(level="distress" if says_safe else "possible_risk", user_says_safe=says_safe)
        else:
            assessment = RiskAssessment(level="possible_risk" if _STRONG.search(text) else "none")

    now = datetime.now(timezone.utc).isoformat()
    if pending and assessment.user_says_safe and assessment.level != "imminent":
        safety.update(status="cleared", cleared_at=now)
        logger.info("[Safety] check-in cleared — resuming coaching")
        return SafetyResult(intercept=False, level=assessment.level)

    if assessment.level == "imminent":
        safety.update(status="check_pending", level="imminent", at=now)
        logger.warning("[Safety] IMMINENT risk detected (%s)", assessment.reason)
        return SafetyResult(intercept=True, message=build_imminent_message(tz), level="imminent")

    if pending:
        safety.update(status="check_pending", at=now)
        logger.warning("[Safety] check-in not cleared (%s)", assessment.reason)
        return SafetyResult(intercept=True, message=build_still_at_risk_message(tz), level=assessment.level)

    if assessment.level == "possible_risk":
        safety.update(status="check_pending", level="possible_risk", at=now, count=int(safety.get("count", 0)) + 1)
        logger.warning("[Safety] possible risk — check-in (%s)", assessment.reason)
        return SafetyResult(intercept=True, message=build_check_in_message(tz), level="possible_risk")

    return SafetyResult(intercept=False, level=assessment.level)
