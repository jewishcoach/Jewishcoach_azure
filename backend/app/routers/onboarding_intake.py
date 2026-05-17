"""
First-entry onboarding intake.

- POST /intake/step — deterministic coach copy + structured slot extraction (LLM extracts only; never writes UX copy).
- POST /intake/stream — removed (410 Gone).
- POST /intake/turn — removed (410 Gone).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ..bsd.llm import get_azure_chat_llm_4o_mini
from ..bsd.onboarding_intake_messages import intake_closing, pick_intake_assistant_message
from ..dependencies import get_current_user
from ..limiter import limiter
from ..models import User
from ..security.chat_input import (
    MAX_CHAT_MESSAGE_CHARS,
    ChatMessageRejected,
    sanitize_chat_message,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

_TRAINING_TOPICS = frozenset(
    {
        "goals",
        "parenting",
        "relationships",
        "career",
        "wellbeing",
        "personal_growth",
    }
)

# Substrings from UI chip labels / typical user taps — avoids a 2nd LLM call when slots are obvious.
_TOPIC_USER_HINTS: dict[str, tuple[str, ...]] = {
    "goals": ("השגת יעדים", "achieving goals"),
    "parenting": ("הורות", "parenting"),
    "relationships": ("זוגיות", "מערכות יחסים", "relationships", "couples"),
    "career": ("קריירה", "עבודה", "career", "work"),
    "wellbeing": ("מצב רוח", "לחץ", "רווחה רגשית", "stress", "wellbeing", "emotional"),
    "personal_growth": ("צמיחה אישית", "personal growth"),
}

# User declines to share a name — must not become display_name / greeting placeholder.
_DISPLAY_NAME_REFUSAL_NORMALIZED: frozenset[str] = frozenset(
    {
        "לא רוצה להגיד",
        "לא רוצה לומר",
        "לא רוצה לומר שם",
        "לא מעוניין לומר",
        "לא מעוניינת לומר",
        "עדיף לא לומר",
        "בלי שם",
        "אין לי שם",
        "לא חשוב",
        "סודי",
        "אנונימי",
        "prefer not to say",
        "rather not say",
        "no name",
        "anonymous",
        "skip",
    }
)

# Single-token lines that look like questions/reactions — never treat as display_name.
_DISPLAY_NAME_JUNK_TOKENS_HE: frozenset[str] = frozenset(
    {
        "מה",
        "למה",
        "איך",
        "מתי",
        "איפה",
        "מי",
        "כמה",
        "נו",
        "אה",
        "הממ",
        "היי",
        "שלום",
        "סבבה",
        "יאללה",
        "בסדר",
        "אוקי",
        "ok",
        "okay",
        "what",
        "why",
        "how",
    }
)


class OnboardingChatMessage(BaseModel):
    """One transcript line; permissive defaults avoid 422 when clients omit empty strings."""

    model_config = ConfigDict(extra="ignore")

    role: Literal["user", "assistant"]
    content: str = Field(default="", max_length=MAX_CHAT_MESSAGE_CHARS)


class KnownOnboardingSlots(BaseModel):
    """Selections already captured in the client UI — authoritative for merge + coach prompt."""

    model_config = ConfigDict(extra="ignore")

    display_name: Optional[str] = Field(default=None, max_length=80)
    gender: Optional[Literal["male", "female"]] = None
    topic: Optional[str] = None
    topics: Optional[list[str]] = None
    topics_skipped: Optional[bool] = None
    gender_skipped: Optional[bool] = None


class OnboardingIntakeRequest(BaseModel):
    # Wide cap pre-coercion — model_validator truncates for the LLM (primary tag ≤16 chars).
    language: str = Field(default="he", max_length=256)
    messages: list[OnboardingChatMessage] = Field(default_factory=list, max_length=48)
    seed_display_name: Optional[str] = Field(default=None, max_length=120)
    known_slots: Optional[KnownOnboardingSlots] = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def coerce_raw_body(cls, data: Any) -> Any:
        """Avoid 422 from minor client/schema drift (null content, wrong role casing, odd language types)."""
        if not isinstance(data, dict):
            return {"language": "he", "messages": [], "seed_display_name": None, "known_slots": None}

        out = dict(data)

        lang_raw = out.get("language", "he")
        if lang_raw is None:
            primary = "he"
        else:
            s = str(lang_raw).strip()
            if not s:
                primary = "he"
            else:
                primary = s.replace("_", "-").split("-")[0].lower()
                if not primary:
                    primary = "he"
                elif primary == "iw":
                    primary = "he"
        out["language"] = primary[:16]

        seed = out.get("seed_display_name")
        if seed is None:
            out["seed_display_name"] = None
        else:
            st = str(seed).strip()
            out["seed_display_name"] = st[:120] if st else None

        raw_msgs = out.get("messages")
        if raw_msgs is None:
            raw_msgs = []
        if not isinstance(raw_msgs, list):
            raw_msgs = []

        fixed: list[dict[str, Any]] = []
        for item in raw_msgs[:48]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            if isinstance(role, str):
                role = role.strip().lower()
            if role not in ("user", "assistant"):
                continue
            content = item.get("content")
            if content is None:
                content = ""
            elif not isinstance(content, str):
                content = str(content)
            if len(content) > MAX_CHAT_MESSAGE_CHARS:
                content = content[:MAX_CHAT_MESSAGE_CHARS]
            fixed.append({"role": role, "content": content})
        out["messages"] = fixed

        raw_known = out.get("known_slots")
        if raw_known is None or raw_known == {}:
            out["known_slots"] = None
        elif isinstance(raw_known, dict):
            topics_raw = raw_known.get("topics")
            topics_list: Optional[list[str]] = None
            if isinstance(topics_raw, list):
                topics_list = [str(x).strip() for x in topics_raw[:16] if str(x).strip()]
            ts_raw = raw_known.get("topics_skipped")
            topics_skipped_v: Optional[bool] = None
            if ts_raw is not None:
                if isinstance(ts_raw, bool):
                    topics_skipped_v = ts_raw
                else:
                    topics_skipped_v = str(ts_raw).strip().lower() in ("true", "1", "yes")

            gs_raw = raw_known.get("gender_skipped")
            gender_skipped_v: Optional[bool] = None
            if gs_raw is not None:
                if isinstance(gs_raw, bool):
                    gender_skipped_v = gs_raw
                else:
                    gender_skipped_v = str(gs_raw).strip().lower() in ("true", "1", "yes")

            nk = _normalize_slots(
                raw_known.get("display_name"),
                raw_known.get("gender"),
                raw_known.get("topic"),
                topics=topics_list,
                topics_skipped=topics_skipped_v,
                gender_skipped=gender_skipped_v,
            )
            compact: dict[str, Any] = {}
            if nk["display_name"] is not None:
                compact["display_name"] = nk["display_name"]
            if nk["gender"] is not None:
                compact["gender"] = nk["gender"]
            if nk["topic"] is not None:
                compact["topic"] = nk["topic"]
            if nk["topics"]:
                compact["topics"] = list(nk["topics"])
            if nk["topics_skipped"]:
                compact["topics_skipped"] = True
            if nk["gender_skipped"]:
                compact["gender_skipped"] = True
            out["known_slots"] = compact if compact else None
        else:
            out["known_slots"] = None

        return out


class OnboardingIntakeResponse(BaseModel):
    assistant_message: str
    display_name: Optional[str] = None
    gender: Optional[Literal["male", "female"]] = None
    topic: Optional[str] = None
    topics: Optional[list[str]] = None
    topics_skipped: bool = False
    gender_skipped: bool = False
    intake_complete: bool = False


class _SlotExtract(BaseModel):
    """LLM output only — no user-facing prose."""

    extracted_display_name: Optional[str] = Field(default=None, max_length=80)
    name_refusal_detected: bool = False
    extracted_gender: Optional[Literal["male", "female"]] = None
    extracted_topic: Optional[str] = None


def _strip_intake_noise(raw: str) -> str:
    return re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", raw).strip()


def _normalize_phrase_for_refusal(raw: str) -> str:
    t = _strip_intake_noise(raw).strip()
    t = re.sub(r"[.!?…,:;\"'`]+$", "", t).strip()
    return re.sub(r"\s+", " ", t).strip()


def _looks_like_interjection_not_name(raw: str) -> bool:
    compact = _normalize_phrase_for_refusal(raw).lower()
    if not compact:
        return True
    if any(c in compact for c in "?？"):
        return True
    words = compact.split()
    if len(words) == 1 and words[0] in _DISPLAY_NAME_JUNK_TOKENS_HE:
        return True
    return False


def _is_display_name_refusal_line(raw: str) -> bool:
    compact = _normalize_phrase_for_refusal(raw).lower()
    if not compact:
        return False
    if compact in _DISPLAY_NAME_REFUSAL_NORMALIZED:
        return True
    # Elliptical / partial typing — still clearly declining (not a name)
    if compact in ("לא רוצה", "לא מעוניין", "לא מעוניינת", "לא רוצה שם", "בלי שם בבקשה"):
        return True
    # Common Hebrew stem phrases
    if "לא רוצה" in compact and ("להגיד" in compact or "לומר" in compact):
        return True
    return False


def _heuristic_gender_from_line(raw: str) -> Optional[str]:
    """Map common Hebrew/English gender replies (free text or chips) without the extractor LLM."""
    t = _strip_intake_noise(raw).strip()
    t = re.sub(r"[.!?…,:;\"'`]+\s*$", "", t).strip()
    t = re.sub(r"^\s*[\"'`]+", "", t).strip()
    if not t:
        return None
    low = t.lower().strip()
    if low in ("male", "m"):
        return "male"
    if low in ("female", "f"):
        return "female"
    spaced = re.sub(r"\s+", " ", low).strip()
    if "i'm male" in spaced or "i am male" in spaced:
        return "male"
    if "i'm female" in spaced or "i am female" in spaced:
        return "female"
    if "אני גבר" in spaced or "אני זכר" in spaced:
        return "male"
    if "אני אישה" in spaced or "אני אשה" in spaced or "אני נקבה" in spaced:
        return "female"
    compact = re.sub(r"\s+", " ", t).strip()
    male_he = frozenset({"זכר", "גבר", "בן"})
    female_he = frozenset({"נקבה", "אישה", "אשה", "בת"})
    if compact in male_he or low in male_he:
        return "male"
    if compact in female_he or low in female_he:
        return "female"
    return None


def _heuristic_gender_skip_from_line(raw: str) -> bool:
    """User declines to share gender — chip text or free-form."""
    c = _normalize_phrase_for_refusal(raw).lower()
    if not c:
        return False
    if c in (
        "prefer not to say",
        "prefer not to share",
        "rather not say",
        "don't want to share",
        "לא רוצה לשתף",
        "לא רוצה לומר",
        "לא משתף מגדר",
        "לא רוצה לשתף מגדר",
        "בלי מגדר",
        "עדיף לא לומר",
    ):
        return True
    needles_en = ("prefer not", "rather not", "skip gender", "no gender")
    needles_he = ("לא רוצה לשתף", "לא רוצה לומר", "לא משתף", "בלי מגדר", "לא רלוונטי למגדר")
    if any(n in c for n in needles_en):
        return True
    if any(n in c for n in needles_he):
        return True
    return False


def _heuristic_display_name_from_line(raw: str) -> Optional[str]:
    t = _strip_intake_noise(raw)
    t = re.sub(r"[.!?…]+\s*$", "", t).strip()
    if _looks_like_interjection_not_name(t):
        return None
    if _is_display_name_refusal_line(t):
        return None
    if _heuristic_gender_skip_from_line(t):
        return None
    if len(t) < 2 or len(t) > 48 or "\n" in t or "\r" in t:
        return None
    if any(c in t for c in ".!?"):
        return None
    if any(ch.isdigit() for ch in t):
        return None
    words = t.split()
    if not words or len(words) > 2:
        return None
    low = t.lower()
    if low in (
        "זכר",
        "נקבה",
        "male",
        "female",
        "גבר",
        "אישה",
        "אשה",
        "בן",
        "בת",
        "m",
        "f",
    ):
        return None
    # Letters / Hebrew / basic punctuation only (aligned with frontend guessDisplayNameFromFirstReply)
    for ch in t.replace(" ", "").replace("-", "").replace("'", "").replace(".", ""):
        if not (ch.isalpha() or ("\u0590" <= ch <= "\u05ff")):
            return None
    return t[:80]


def _heuristic_display_name_loose(raw: str) -> Optional[str]:
    """Up to 3 words — mirrors frontend looseNameFromFirstReply for name-phase completion."""
    t = _strip_intake_noise(raw)
    t = re.sub(r"[.!?…]+\s*$", "", t).strip()
    if len(t) < 2 or len(t) > 48 or "\n" in t or "\r" in t:
        return None
    if any(c in t for c in "?？"):
        return None
    if _looks_like_interjection_not_name(t):
        return None
    if _is_display_name_refusal_line(t):
        return None
    if _heuristic_gender_skip_from_line(t):
        return None
    if any(ch.isdigit() for ch in t):
        return None
    words = t.split()
    if not words or len(words) > 3:
        return None
    if max(len(w) for w in words) > 22:
        return None
    low = t.lower()
    if low in (
        "זכר",
        "נקבה",
        "male",
        "female",
        "גבר",
        "אישה",
        "אשה",
        "בן",
        "בת",
        "m",
        "f",
    ):
        return None
    for ch in t.replace(" ", "").replace("-", "").replace("'", "").replace(".", ""):
        if not (ch.isalpha() or ("\u0590" <= ch <= "\u05ff")):
            return None
    return t[:80]


def _dedupe_topics(ids: Optional[list[str]]) -> tuple[str, ...]:
    if not ids:
        return ()
    seen: list[str] = []
    for x in ids:
        t = _slug(str(x).strip() if x is not None else None)
        if t in _TRAINING_TOPICS and t not in seen:
            seen.append(t)
    return tuple(seen)


def _heuristic_slots_from_transcript(msgs: list[OnboardingChatMessage]) -> dict[str, Any]:
    """Infer slots from user lines (chip taps, short names) without calling the extractor LLM."""
    out = _normalize_slots(None, None, None)
    topic_acc: list[str] = []
    for m in msgs:
        if m.role != "user":
            continue
        raw = _strip_intake_noise(m.content.strip())
        if not raw:
            continue
        low = raw.lower()
        if out["gender"] is None:
            hg = _heuristic_gender_from_line(raw)
            if hg:
                out["gender"] = hg
                out["gender_skipped"] = False
            elif not out.get("gender_skipped") and _heuristic_gender_skip_from_line(raw):
                out["gender_skipped"] = True
                out["gender"] = None
        for tid, needles in _TOPIC_USER_HINTS.items():
            if tid in topic_acc:
                continue
            if any(n.lower() in low or n in raw for n in needles):
                topic_acc.append(tid)
        if out["display_name"] is None:
            guessed = _heuristic_display_name_from_line(raw) or _heuristic_display_name_loose(raw)
            if guessed:
                out["display_name"] = guessed
    if topic_acc:
        tup = tuple(topic_acc)
        out["topics"] = tup
        out["topic"] = tup[0]
    return out


def _apply_heuristic_fill(slots: dict[str, Any], heur: dict[str, Any]) -> dict[str, Any]:
    merged = dict(slots)
    if heur.get("gender") in ("male", "female"):
        merged["gender"] = heur["gender"]
        merged["gender_skipped"] = False
    elif merged.get("gender") not in ("male", "female") and not merged.get("gender_skipped"):
        if heur.get("gender_skipped"):
            merged["gender_skipped"] = True
            merged["gender"] = None

    if merged.get("topics_skipped"):
        if merged.get("display_name") is None and heur.get("display_name") is not None:
            merged["display_name"] = heur["display_name"]
        return merged

    if merged.get("display_name") is None and heur.get("display_name") is not None:
        merged["display_name"] = heur["display_name"]

    if merged.get("topic") is None and heur.get("topic") is not None:
        merged["topic"] = heur["topic"]

    ht = heur.get("topics") or ()
    mt = merged.get("topics") or ()
    if ht:
        u = _dedupe_topics(list(mt) + list(ht))
        if u:
            merged["topics"] = u
            merged["topic"] = u[0]
    return merged


def _slug(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    t = str(s).strip()
    return t or None


def _normalize_slots(
    display_name: Optional[str],
    gender: Optional[str],
    topic: Optional[str],
    *,
    topics: Optional[list[str]] = None,
    topics_skipped: Optional[bool] = None,
    gender_skipped: Optional[bool] = None,
) -> dict[str, Any]:
    skipped = bool(topics_skipped)
    merged_topics = () if skipped else _dedupe_topics([*(topics or []), *([topic] if topic else [])])
    gen = gender
    if gen not in ("male", "female", None):
        gen = None
    gskip = bool(gender_skipped)
    if gskip:
        gen = None
    name = _slug(display_name)
    tp = merged_topics[0] if merged_topics else None
    return {
        "display_name": name,
        "gender": gen,
        "topic": tp,
        "topics": merged_topics,
        "topics_skipped": skipped,
        "gender_skipped": gskip,
    }


def _ensure_topics_sync(slots: dict[str, Any]) -> dict[str, Any]:
    if slots.get("topics_skipped"):
        slots["topics"] = ()
        slots["topic"] = None
        return slots
    topics = slots.get("topics") or ()
    if isinstance(topics, list):
        topics = _dedupe_topics(topics)
    else:
        topics = _dedupe_topics(list(topics))
    slots["topics"] = topics
    slots["topic"] = topics[0] if topics else None
    return slots


def _name_collection_resolved(
    slots: dict[str, Any],
    msgs: list[OnboardingChatMessage],
    *,
    extractor_refusal: bool = False,
) -> bool:
    if extractor_refusal:
        return True
    if (slots.get("display_name") or "").strip():
        return True
    for m in msgs:
        if m.role != "user":
            continue
        raw = m.content.strip()
        if _is_display_name_refusal_line(raw):
            return True
        if _heuristic_display_name_from_line(raw) or _heuristic_display_name_loose(raw):
            return True
    return False


def _slots_complete(slots: dict[str, Any]) -> bool:
    """Name is optional (user may decline); gender or explicit skip; topic optional if user skipped."""
    gender_ok = slots.get("gender") in ("male", "female") or bool(slots.get("gender_skipped"))
    if not gender_ok:
        return False
    if slots.get("topics_skipped"):
        return True
    topics = slots.get("topics") or ()
    return len(topics) >= 1


def _missing_focus(
    slots: dict[str, Any],
    msgs: list[OnboardingChatMessage],
    *,
    extractor_refusal: bool = False,
) -> Optional[str]:
    if not _name_collection_resolved(slots, msgs, extractor_refusal=extractor_refusal):
        return "display_name"
    gender_ok = slots.get("gender") in ("male", "female") or bool(slots.get("gender_skipped"))
    if not gender_ok:
        return "gender"
    topics = slots.get("topics") or ()
    if not topics and not slots.get("topics_skipped"):
        return "topic"
    return None


def _scrub_refusal_display_name(slots: dict[str, Any]) -> None:
    dn = slots.get("display_name")
    if isinstance(dn, str) and dn.strip():
        if _is_display_name_refusal_line(dn) or _heuristic_gender_skip_from_line(dn):
            slots["display_name"] = None


def _merge_known_into_slots(
    extracted: dict[str, Any],
    known: Optional[KnownOnboardingSlots],
) -> dict[str, Any]:
    """Client/UI selections win over model extraction when provided."""
    if known is None:
        return _ensure_topics_sync(dict(extracted))
    out = dict(extracted)
    if known.display_name is not None:
        out["display_name"] = _slug(known.display_name)
    if known.gender_skipped:
        out["gender_skipped"] = True
        out["gender"] = None
    elif known.gender in ("male", "female"):
        out["gender"] = known.gender
        out["gender_skipped"] = False

    if known.topics_skipped:
        out["topics_skipped"] = True
        out["topics"] = ()
        out["topic"] = None
    else:
        tl: list[str] = []
        if known.topics:
            tl.extend(str(x) for x in known.topics)
        if known.topic:
            tl.append(str(known.topic))
        merged = _dedupe_topics(tl)
        if merged:
            out["topics"] = merged
            out["topic"] = merged[0]
            out["topics_skipped"] = False

    return _ensure_topics_sync(out)




def _sanitize_transcript(body: OnboardingIntakeRequest) -> list[OnboardingChatMessage]:
    msgs = body.messages[-40:]
    if msgs:
        last = msgs[-1]
        if last.role != "user":
            raise HTTPException(status_code=400, detail="Last transcript message must be from the user")
        try:
            sanitized_last = sanitize_chat_message(last.content)
        except ChatMessageRejected as e:
            raise HTTPException(status_code=400, detail=e.reason) from e
        msgs = [*msgs[:-1], OnboardingChatMessage(role="user", content=sanitized_last)]
    return msgs


def _user_turn_count(msgs: list[OnboardingChatMessage]) -> int:
    return sum(1 for m in msgs if m.role == "user")


def _last_user_text(msgs: list[OnboardingChatMessage]) -> str:
    for m in reversed(msgs):
        if m.role == "user":
            return _strip_intake_noise(m.content.strip())
    return ""


def _extractor_transcript_human(msgs: list[OnboardingChatMessage], language: str) -> HumanMessage:
    lines: list[str] = []
    for m in msgs[-14:]:
        tag = "User" if m.role == "user" else "Coach"
        lines.append(f"{tag}: {m.content}")
    body = "[Recent transcript]\n" + "\n".join(lines)
    if (language or "he").lower().startswith("he"):
        body += (
            "\n\nחלץ לפי כל ההיסטוריה; למגדר ולנושא עדיף להסתמך בעיקר על ההודעה האחרונה של המשתמש."
        )
    else:
        body += "\n\nExtract using the full transcript; weight the user's latest message for gender/topic."
    return HumanMessage(content=body)


def _build_slot_extractor_system_prompt(
    language: str,
    seed_display_name: Optional[str],
    slots_snapshot: dict[str, Any],
) -> str:
    codes = ", ".join(sorted(_TRAINING_TOPICS))
    lang_he = (language or "he").lower().startswith("he")
    seed = (seed_display_name or "").strip()
    seed_note = ""
    if seed:
        seed_note = (
            f"\nרמז שם מההרשמה (אופציונלי): {seed[:80]}.\n"
            if lang_he
            else f"\nOptional signup name hint: {seed[:80]}.\n"
        )
    bits: list[str] = []
    dn = (slots_snapshot.get("display_name") or "").strip()
    if dn:
        bits.append(f"name={dn}")
    if slots_snapshot.get("gender") in ("male", "female"):
        bits.append(f"gender={slots_snapshot['gender']}")
    if slots_snapshot.get("gender_skipped"):
        bits.append("gender_skipped=yes")
    if slots_snapshot.get("topics_skipped"):
        bits.append("topics_skipped=yes")
    else:
        ts = slots_snapshot.get("topics") or ()
        if ts:
            bits.append("topics=" + ",".join(ts))
        elif slots_snapshot.get("topic") in _TRAINING_TOPICS:
            bits.append(f"topic={slots_snapshot['topic']}")
    known_line = ", ".join(bits) if bits else ("(ריק)" if lang_he else "(empty)")

    if lang_he:
        return (
            "אתה מחלץ שדות קליטה בלבד ל‑BSD — בלי טקסט למשתמש.\n"
            "פלט: extracted_display_name, name_refusal_detected, extracted_gender, extracted_topic בלבד.\n\n"
            "• extracted_display_name — עד 3 מילים, בלי ספרות; null אם אין שם ברור.\n"
            "• name_refusal_detected=true רק כשהמשתמש מסרב במפורש לתת שם.\n"
            "• extracted_gender — male/female רק אם נאמר במפורש; אסור להסיק משם פרטי → אחרת null.\n"
            f"• extracted_topic — אחד מ־{codes} או null אם לא נאמר במפורש.\n"
            "מפה ביטויי צ'יפים בעברית לקוד הנושא המתאים.\n\n"
            f"תמונת מצב מהמערכת: {known_line}\n"
            f"{seed_note}"
        )

    return (
        "Extract BSD onboarding slots ONLY — no prose for the user.\n"
        "Output: extracted_display_name, name_refusal_detected, extracted_gender, extracted_topic.\n\n"
        "• extracted_display_name — ≤3 words, no digits; null if unclear.\n"
        "• name_refusal_detected=true only on explicit refusal to share a name.\n"
        "• extracted_gender — male/female only if explicitly stated; NEVER infer from names → else null.\n"
        f"• extracted_topic — one of {codes}, or null unless explicit.\n\n"
        f"Snapshot: {known_line}\n"
        f"{seed_note}"
    )


def _apply_extractor_patch(
    slots: dict[str, Any],
    ext: _SlotExtract,
    *,
    missing_before: str,
) -> None:
    if ext.name_refusal_detected:
        slots["display_name"] = None

    cand = _slug(ext.extracted_display_name)
    if cand and not ext.name_refusal_detected:
        if (
            not _is_display_name_refusal_line(cand)
            and not _looks_like_interjection_not_name(cand)
            and not _heuristic_gender_skip_from_line(cand)
        ):
            if missing_before == "display_name" or not (slots.get("display_name") or "").strip():
                slots["display_name"] = cand

    if ext.extracted_gender in ("male", "female") and not slots.get("gender_skipped"):
        slots["gender"] = ext.extracted_gender
        slots["gender_skipped"] = False

    if slots.get("topics_skipped"):
        return

    tp = _slug(ext.extracted_topic)
    if tp in _TRAINING_TOPICS:
        cur = list(slots.get("topics") or ())
        if tp not in cur:
            cur.append(tp)
        tup = _dedupe_topics(cur)
        slots["topics"] = tup
        slots["topic"] = tup[0] if tup else None


def _gender_guard_clear_if_hallucinated(
    slots: dict[str, Any],
    msgs: list[OnboardingChatMessage],
    extracted_gender_fallback: Optional[str],
) -> None:
    """Drop gender if last user line looks like name-only/junk but model guessed gender."""
    lu = _last_user_text(msgs)
    if _heuristic_gender_skip_from_line(lu):
        slots["gender_skipped"] = True
        slots["gender"] = None
        return
    hg = _heuristic_gender_from_line(lu)
    if hg:
        slots["gender"] = hg
        slots["gender_skipped"] = False
        return
    if slots.get("gender") not in ("male", "female"):
        return
    last_suggests_name_only = bool(
        _heuristic_display_name_from_line(lu) or _heuristic_display_name_loose(lu)
    )
    junk_line = bool(lu.strip()) and _looks_like_interjection_not_name(lu)
    if extracted_gender_fallback in ("male", "female") and (last_suggests_name_only or junk_line):
        slots["gender"] = None


async def _load_onboarding_intake_request(request: Request) -> OnboardingIntakeRequest:
    """
    Parse POST JSON without FastAPI's automatic body model injection.

    Some proxies/clients still trigger Starlette/FastAPI RequestValidationError (HTTP 422)
    before our route runs; reading and validating manually avoids that entirely.
    """
    raw = await request.body()
    if not raw or not raw.strip():
        data: dict[str, Any] = {}
    else:
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("[onboarding_intake] invalid JSON body: %s", type(exc).__name__)
            parsed = {}
        data = parsed if isinstance(parsed, dict) else {}
    try:
        return OnboardingIntakeRequest.model_validate(data)
    except ValidationError as exc:
        logger.warning("[onboarding_intake] body coerce failed, using defaults: %s", exc.errors()[:5])
        return OnboardingIntakeRequest.model_validate({})


def _topics_payload(slots: dict[str, Any]) -> dict[str, Any]:
    tops = slots.get("topics") or ()
    return {
        "topic": slots.get("topic"),
        "topics": list(tops) if tops else None,
        "topics_skipped": bool(slots.get("topics_skipped")),
        "gender_skipped": bool(slots.get("gender_skipped")),
    }


@router.post("/intake/step", response_model=OnboardingIntakeResponse)
@limiter.limit("40/minute")
async def onboarding_intake_step(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Single onboarding turn: LLM extracts slots only; assistant_message is deterministic server copy.
    """
    _ = current_user
    body = await _load_onboarding_intake_request(request)
    msgs = _sanitize_transcript(body)

    empty = _normalize_slots(None, None, None)
    slots = _merge_known_into_slots(empty, body.known_slots)
    heur = _heuristic_slots_from_transcript(msgs)
    slots = _apply_heuristic_fill(slots, heur)
    _scrub_refusal_display_name(slots)
    _ensure_topics_sync(slots)

    missing_before = _missing_focus(slots, msgs)

    if missing_before is None:
        return OnboardingIntakeResponse(
            assistant_message=intake_closing(body.language),
            display_name=slots.get("display_name"),
            gender=slots.get("gender"),
            intake_complete=True,
            **_topics_payload(slots),
        )

    sys_prompt = _build_slot_extractor_system_prompt(body.language, body.seed_display_name, slots)
    lc_messages: list = [
        SystemMessage(content=sys_prompt),
        _extractor_transcript_human(msgs, body.language),
    ]

    try:
        llm = get_azure_chat_llm_4o_mini()
        structured_llm = llm.with_structured_output(
            _SlotExtract,
            method="function_calling",
            include_raw=True,
        )
        packed = await structured_llm.ainvoke(lc_messages)
        parsed = packed.get("parsed")
        if parsed is None:
            logger.warning("[onboarding_intake] slot extract parse missing raw=%s", packed.get("raw"))
            raise HTTPException(status_code=502, detail="Intake step unavailable")
        ext_model = parsed if isinstance(parsed, _SlotExtract) else _SlotExtract.model_validate(parsed)
        extracted_guess = ext_model.extracted_gender

        _apply_extractor_patch(slots, ext_model, missing_before=missing_before)
        slots = _apply_heuristic_fill(slots, heur)
        _scrub_refusal_display_name(slots)

        _gender_guard_clear_if_hallucinated(slots, msgs, extracted_guess)

        extractor_refusal = bool(ext_model.name_refusal_detected)
        _ensure_topics_sync(slots)
        missing_after = _missing_focus(slots, msgs, extractor_refusal=extractor_refusal)

        if missing_after is None:
            return OnboardingIntakeResponse(
                assistant_message=intake_closing(body.language),
                display_name=slots.get("display_name"),
                gender=slots.get("gender"),
                intake_complete=True,
                **_topics_payload(slots),
            )

        ut_count = _user_turn_count(msgs)
        amsg = pick_intake_assistant_message(
            body.language,
            missing=missing_after,
            gender=slots.get("gender"),
            user_message_count=ut_count,
            gender_skipped=bool(slots.get("gender_skipped")),
        )

        intake_complete = _slots_complete(slots)
        return OnboardingIntakeResponse(
            assistant_message=amsg,
            display_name=slots.get("display_name"),
            gender=slots.get("gender"),
            intake_complete=intake_complete,
            **_topics_payload(slots),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("[onboarding_intake] step failure lang=%s", body.language)
        raise HTTPException(status_code=502, detail="Intake step failed") from None


_DEPRECATED_INTAKE = (
    "Onboarding intake legacy endpoint removed. Use POST /api/onboarding/intake/step only."
)


@router.post("/intake/stream")
@limiter.limit("40/minute")
async def onboarding_intake_stream(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    _ = request
    raise HTTPException(status_code=410, detail=_DEPRECATED_INTAKE)


@router.post("/intake/turn", response_model=OnboardingIntakeResponse)
@limiter.limit("40/minute")
async def onboarding_intake_turn(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    _ = request
    raise HTTPException(status_code=410, detail=_DEPRECATED_INTAKE)
