"""
LLM-powered first-entry onboarding: streaming coach replies + structured slot extraction.

- POST /intake/stream — SSE: token chunks then final JSON with slots (recommended UX).
- POST /intake/turn — single structured response (fallback / simple clients).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, AsyncIterator, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ..bsd.llm import get_azure_chat_llm_4o_mini
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

_EXTRACT_MAX_MESSAGES = 16


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
            nk = _normalize_slots(
                raw_known.get("display_name"),
                raw_known.get("gender"),
                raw_known.get("topic"),
            )
            compact = {k: v for k, v in nk.items() if v is not None}
            out["known_slots"] = compact if compact else None
        else:
            out["known_slots"] = None

        return out


class OnboardingIntakeResponse(BaseModel):
    assistant_message: str
    display_name: Optional[str] = None
    gender: Optional[Literal["male", "female"]] = None
    topic: Optional[str] = None
    intake_complete: bool = False


class _StructuredTurn(BaseModel):
    assistant_message: str = Field(..., max_length=4000)
    display_name: Optional[str] = Field(default=None, max_length=80)
    gender: Optional[Literal["male", "female"]] = None
    topic: Optional[str] = None


class _SlotsOnly(BaseModel):
    """Post-reply extraction — cumulative slots from full transcript + latest coach text."""

    display_name: Optional[str] = Field(default=None, max_length=80)
    gender: Optional[Literal["male", "female"]] = None
    topic: Optional[str] = None


def _trim_messages_for_extract(msgs: list[OnboardingChatMessage]) -> list[OnboardingChatMessage]:
    if len(msgs) <= _EXTRACT_MAX_MESSAGES:
        return msgs
    return msgs[-_EXTRACT_MAX_MESSAGES:]


def _strip_intake_noise(raw: str) -> str:
    return re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", raw).strip()


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
    compact = re.sub(r"\s+", " ", t).strip()
    male_he = frozenset({"זכר", "גבר", "בן"})
    female_he = frozenset({"נקבה", "אישה", "אשה", "בת"})
    if compact in male_he or low in male_he:
        return "male"
    if compact in female_he or low in female_he:
        return "female"
    return None


def _heuristic_display_name_from_line(raw: str) -> Optional[str]:
    t = _strip_intake_noise(raw)
    t = re.sub(r"[.!?…]+\s*$", "", t).strip()
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


def _heuristic_slots_from_transcript(msgs: list[OnboardingChatMessage]) -> dict[str, Any]:
    """Infer slots from user lines (chip taps, short names) without calling the extractor LLM."""
    out = _normalize_slots(None, None, None)
    for m in reversed(msgs):
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
        if out["topic"] is None:
            for tid, needles in _TOPIC_USER_HINTS.items():
                if any(n.lower() in low or n in raw for n in needles):
                    out["topic"] = tid
                    break
        if out["display_name"] is None:
            guessed = _heuristic_display_name_from_line(raw)
            if guessed:
                out["display_name"] = guessed
    return out


def _apply_heuristic_fill(slots: dict[str, Any], heur: dict[str, Any]) -> dict[str, Any]:
    merged = dict(slots)
    for k in ("display_name", "gender", "topic"):
        if merged.get(k) is None and heur.get(k) is not None:
            merged[k] = heur[k]
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
) -> dict[str, Any]:
    tp = _slug(topic)
    if tp is not None and tp not in _TRAINING_TOPICS:
        tp = None
    gen = gender
    if gen not in ("male", "female", None):
        gen = None
    name = _slug(display_name)
    return {
        "display_name": name,
        "gender": gen,
        "topic": tp,
    }


def _sanitize_enums_turn(parsed: _StructuredTurn) -> dict[str, Any]:
    base = _normalize_slots(parsed.display_name, parsed.gender, parsed.topic)
    base["assistant_message"] = (parsed.assistant_message or "").strip() or "…"
    return base


def _sanitize_enums_slots(parsed: _SlotsOnly) -> dict[str, Any]:
    return _normalize_slots(parsed.display_name, parsed.gender, parsed.topic)


def _slots_complete(slots: dict[str, Any]) -> bool:
    return bool(
        slots.get("display_name")
        and slots.get("gender") in ("male", "female")
        and slots.get("topic") in _TRAINING_TOPICS
    )


def _merge_known_into_slots(
    extracted: dict[str, Any],
    known: Optional[KnownOnboardingSlots],
) -> dict[str, Any]:
    """Client/UI selections win over model extraction when provided."""
    if known is None:
        return extracted
    kn = _normalize_slots(known.display_name, known.gender, known.topic)
    out = dict(extracted)
    for key in ("display_name", "gender", "topic"):
        if kn.get(key) is not None:
            out[key] = kn[key]
    return out


def _known_slots_prompt_fragment(known: Optional[KnownOnboardingSlots]) -> str:
    if known is None:
        return ""
    kn = _normalize_slots(known.display_name, known.gender, known.topic)
    lines: list[str] = []
    if kn["display_name"]:
        lines.append(f"- Name to use: {kn['display_name']}")
    if kn["gender"] in ("male", "female"):
        lines.append(f"- Gender: {kn['gender']}")
    if kn["topic"]:
        lines.append(f"- Training focus topic (internal): {kn['topic']}")
    if not lines:
        return ""
    return (
        "\nThe product UI already recorded the items below (internal codes shown for you only). "
        "Do not ask those questions again unless the user clearly contradicts them. "
        "Speak naturally — never read codes aloud. Continue only with topics still missing.\n"
        + "\n".join(lines)
        + "\n"
    )


def _known_slots_for_llm_prompt(
    known: Optional[KnownOnboardingSlots],
    msgs: list[OnboardingChatMessage],
) -> Optional[KnownOnboardingSlots]:
    """Merge client known_slots with transcript heuristics before the reply LLM runs."""
    heur = _heuristic_slots_from_transcript(msgs)
    empty = _normalize_slots(None, None, None)
    merged = _apply_heuristic_fill(_merge_known_into_slots(empty, known), heur)
    if not any(merged.get(k) for k in ("display_name", "gender", "topic")):
        return known
    try:
        return KnownOnboardingSlots.model_validate(
            {
                "display_name": merged.get("display_name"),
                "gender": merged.get("gender"),
                "topic": merged.get("topic"),
            }
        )
    except ValidationError:
        safe_topic = merged.get("topic")
        if safe_topic not in _TRAINING_TOPICS:
            safe_topic = None
        safe_gender = merged.get("gender")
        if safe_gender not in ("male", "female"):
            safe_gender = None
        dn = merged.get("display_name")
        safe_name = (dn[:80] if isinstance(dn, str) and dn.strip() else None)
        try:
            return KnownOnboardingSlots.model_validate(
                {
                    "display_name": safe_name,
                    "gender": safe_gender,
                    "topic": safe_topic,
                }
            )
        except ValidationError:
            return known


def _turn_constraint_message(known_slots: Optional[KnownOnboardingSlots]) -> HumanMessage:
    """Per-turn reminder so the model does not re-ask slots already captured in UI/transcript."""
    kn = _normalize_slots(
        known_slots.display_name if known_slots else None,
        known_slots.gender if known_slots else None,
        known_slots.topic if known_slots else None,
    )
    filled: list[str] = []
    if kn["display_name"]:
        filled.append(f"name={kn['display_name']}")
    if kn["gender"] in ("male", "female"):
        filled.append(f"gender={kn['gender']}")
    if kn["topic"]:
        filled.append(f"topic={kn['topic']}")
    missing: list[str] = []
    if not kn["display_name"]:
        missing.append("display_name (what to call them)")
    if kn["gender"] not in ("male", "female"):
        missing.append("gender (male/female)")
    if not kn["topic"]:
        missing.append("training topic (UI chips)")
    filled_s = "; ".join(filled) if filled else "(nothing confirmed yet)"
    missing_s = "; ".join(missing) if missing else "(nothing — all slots filled; closing only)"
    forbid_name = ""
    if kn["display_name"]:
        forbid_name = (
            "FORBIDDEN in your reply (do not express these in any wording): asking again what to call them, "
            "nickname, 'preferred name', or Hebrew like "
            "'איך לקרוא לך', 'איך תרצה שנקרא', 'באיזה שם', 'בשם מה לפנות אליך'. "
            f"The display name is ALREADY «{kn['display_name']}» — use it and proceed.\n"
        )
    forbid_gender = ""
    if kn["gender"] in ("male", "female"):
        gtxt = "male (masculine Hebrew)" if kn["gender"] == "male" else "female (feminine Hebrew)"
        forbid_gender = (
            "FORBIDDEN: any question, confirmation, hedging, or re-check about gender, sex, "
            "or Hebrew grammatical gender — including «נכון?», «סתם לוודא», «מזדהה כגבר», «גבר או אישה», "
            "«זכר או נקבה», «לשון זכר או נקבה», «בלשון זכר או בלשון נקבה», "
            "«איך אתה מעדיף שאדבר», or asking again how to conjugate. "
            f"The grammatical gender for Hebrew is ALREADY «{gtxt}». Acknowledge briefly if needed, then continue.\n"
        )
    forbid_topic = ""
    if kn["topic"]:
        forbid_topic = "FORBIDDEN: asking which coaching topic again — topic already confirmed.\n"
    he_grammar = ""
    if kn["gender"] == "male":
        he_grammar = (
            "Hebrew: user is male — when addressing them use masculine second-person forms "
            "(e.g. אתה, שלך, מוכן).\n"
        )
    elif kn["gender"] == "female":
        he_grammar = (
            "Hebrew: user is female — when addressing them use feminine second-person forms "
            "(e.g. את, שלך, מוכנה).\n"
        )
    body = (
        "[Hard constraint for THIS reply — follow exactly]\n"
        f"Already confirmed (do not ask again): {filled_s}\n"
        f"You may only move toward: {missing_s}\n"
        "Never ask again about gender or topic if they appear under confirmed.\n"
        "If the user's latest message is a chip tap (topic/gender), accept it — do not re-ask.\n"
        + forbid_name
        + forbid_gender
        + forbid_topic
        + he_grammar
        + "If nothing is missing, write a short warm closing with no questions."
    )
    return HumanMessage(content=body)


def _build_reply_system_prompt(
    language: str,
    seed_display_name: Optional[str],
    known_slots: Optional[KnownOnboardingSlots] = None,
) -> str:
    lang = (language or "he").lower()
    primary = "Hebrew" if lang.startswith("he") else "English"
    hint = ""
    if seed_display_name and seed_display_name.strip():
        hint = (
            f"\nOptional signup/profile name hint (use ONLY if the user has not clearly chosen "
            f"a different name in the transcript — their stated name always wins): "
            f"{seed_display_name.strip()[:80]}\n"
        )
    known_frag = _known_slots_prompt_fragment(known_slots)
    return f"""You are the BSD Jewish Coach intake assistant — warm, concise, respectful.
Write ONLY in {primary} (the user's locale).
{known_frag}{hint}
Have a SHORT natural conversation (often about 3–6 user turns) to collect ONLY:
1) What to call them (display name)
2) Gender for Hebrew grammar — politely; only male or female in our product (often picked via UI buttons)
3) Which coaching-life focus fits best — the UI offers topic chips such as goals, parenting, relationships, career, wellbeing, personal growth (internal codes only — never say codes aloud)

Rules:
- The first assistant message in the transcript often already asks for their name (e.g. «מה שמך», «What's your name»).
  If the user's next short reply looks like a name, that reply IS their display name — never ask again how to address them (no rephrased name question).
- When a UI context block lists facts already recorded, do NOT ask those again unless the user clearly contradicts them.
- If display_name is already recorded (UI block or prior answer to «what's your name?»), NEVER ask again how to call them —
  no Hebrew variants («איך לקרוא לך», «איך תרצה שנקרא», וכו'): greet once with that name and continue to the next missing slot.
- If BOTH gender and topic are still missing, ask ONLY for gender first in this reply — do NOT mention topic choice yet.
- Do NOT repeat the same question across turns; one missing item per message when possible.
- Hebrew before gender is known: avoid feminine second-person agreement toward the user (do not use «שמחה לפגוש אותך» as if they are female).
  Prefer neutral wording («נעים להכיר», «טוב לפגוש אותך», «שמח להכיר») until gender is confirmed; once female is confirmed, switch fully to feminine agreement.
- Do NOT verbally drill topic buttons — briefly acknowledge and invite continuing when those picks appear.
- If gender is already confirmed, never ask male/female again — including confirmations («נכון?», «רק לוודא»); match Hebrew second-person grammar and move on.
- If the user's latest message is clearly their name (or corrects an earlier wrong greeting), treat it as final:
  use only that name from now on — do not ask them to pick between it and an outdated hint or a mistaken opener.
- If they answer several things at once, acknowledge warmly.
- Never output JSON, bullet lists of internal codes, or markup — natural prose only.
- Keep replies brief (usually 1–3 short paragraphs).
- When name, gender, and topic are all known, close warmly: affirm they are in the right place and that coaching can begin soon — invite them to enter the app (do not start a long coaching session here).
"""


def _build_extract_system_prompt() -> str:
    codes = ", ".join(sorted(_TRAINING_TOPICS))
    return f"""You extract onboarding slots from a coaching intake transcript (Hebrew and/or English).

Return CUMULATIVE best-known values from the ENTIRE transcript plus the coach's latest reply:
- display_name: short name to call the user; null if unknown.
- gender: only "male" or "female"; null if not stated.
- topic: exactly one of {codes} — or null if unknown.
  goals=achieving goals / targets; parenting=parenthood / kids; relationships=couple / intimate relationship;
  career=work / career; wellbeing=stress / balance / emotional wellbeing; personal_growth=general self growth.

Use null whenever uncertain. Do not invent.
If the user's message is only זכר, נקבה, Male, or Female (typical UI chip taps), set gender to male/female accordingly — do not leave gender null after such a line.
If the user replied with a short name right after being asked what to call them, set display_name to that reply
even when the assistant greeting used a different placeholder.
If the user selected a topic by tapping a UI label, map common Hebrew chip text to topic:
- wellbeing: mood/stress/wellbeing phrasing (e.g. מצב רוח, לחץ, רווחה רגשית)
- goals: השגת יעדים
- parenting: הורות
- relationships: זוגיות / מערכות יחסים
- career: קריירה / עבודה
- personal_growth: צמיחה אישית
English chip phrases map similarly (Achieving goals → goals; Parenting → parenting; etc.)."""


def _history_to_lc(messages: list[OnboardingChatMessage]) -> list:
    out = []
    for m in messages:
        if m.role == "user":
            out.append(HumanMessage(content=m.content))
        else:
            out.append(AIMessage(content=m.content))
    return out


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


def _lc_messages_for_reply(
    language: str,
    seed: Optional[str],
    msgs: list[OnboardingChatMessage],
    known_slots: Optional[KnownOnboardingSlots] = None,
) -> list:
    sys = _build_reply_system_prompt(language, seed, known_slots)
    lc_messages: list = [SystemMessage(content=sys)]
    lc_messages.extend(_history_to_lc(msgs))
    if msgs:
        lc_messages.append(_turn_constraint_message(known_slots))
    elif not msgs:
        name_from_known = (
            _normalize_slots(
                known_slots.display_name,
                None,
                None,
            ).get("display_name")
            if known_slots
            else None
        )

        has_name_hint = bool(name_from_known or (seed and str(seed).strip()))
        if has_name_hint:
            lc_messages.append(
                HumanMessage(
                    content=(
                        "[Session start — no user message yet.] "
                        "Brief opening greeting. A name may already be known from signup or the UI — confirm it warmly "
                        "instead of asking from scratch. Then continue only with intake topics still missing."
                    )
                )
            )
        else:
            lc_messages.append(
                HumanMessage(
                    content=(
                        "[Session start — no user message yet.] "
                        "Send only your opening greeting and ask how they wish to be called."
                    )
                )
            )
    return lc_messages


def _chunk_text(chunk: Any) -> str:
    c = getattr(chunk, "content", None)
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts: list[str] = []
        for p in c:
            if isinstance(p, dict) and p.get("type") == "text":
                parts.append(str(p.get("text", "")))
            elif isinstance(p, str):
                parts.append(p)
        return "".join(parts)
    return ""


async def _extract_slots(
    msgs: list[OnboardingChatMessage],
    assistant_reply: str,
) -> dict[str, Any]:
    transcript = [{"role": m.role, "content": m.content} for m in msgs]
    human = (
        json.dumps(transcript, ensure_ascii=False)
        + "\n\nLatest coach reply:\n"
        + (assistant_reply or "").strip()
    )
    llm = get_azure_chat_llm_4o_mini()
    structured_llm = llm.with_structured_output(_SlotsOnly, method="function_calling", include_raw=True)
    packed = await structured_llm.ainvoke(
        [SystemMessage(content=_build_extract_system_prompt()), HumanMessage(content=human)]
    )
    parsed = packed.get("parsed")
    if parsed is None:
        logger.warning("[onboarding_intake] extract parse missing")
        return _normalize_slots(None, None, None)
    return _sanitize_enums_slots(parsed)


async def _stream_reply_tokens(lc_messages: list) -> AsyncIterator[str]:
    llm = get_azure_chat_llm_4o_mini()
    async for chunk in llm.astream(lc_messages):
        piece = _chunk_text(chunk)
        if piece:
            yield piece


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


@router.post("/intake/stream")
@limiter.limit("40/minute")
async def onboarding_intake_stream(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """SSE stream: many `data: {\"content\":\"...\"}` lines, then `data: {\"done\":true,...slots}`"""
    _ = current_user
    body = await _load_onboarding_intake_request(request)

    async def event_gen() -> AsyncIterator[str]:
        try:
            msgs = _sanitize_transcript(body)
            prompt_known = _known_slots_for_llm_prompt(body.known_slots, msgs)
            lc_messages = _lc_messages_for_reply(
                body.language, body.seed_display_name, msgs, prompt_known
            )
            full_reply = ""
            async for piece in _stream_reply_tokens(lc_messages):
                full_reply += piece
                yield f"data: {json.dumps({'content': piece})}\n\n"

            empty = _normalize_slots(None, None, None)
            slots = _merge_known_into_slots(empty, body.known_slots)
            heur = _heuristic_slots_from_transcript(msgs)
            slots = _apply_heuristic_fill(slots, heur)

            if not _slots_complete(slots):
                extracted = await _extract_slots(_trim_messages_for_extract(msgs), full_reply)
                slots = _merge_known_into_slots(extracted, body.known_slots)
                slots = _apply_heuristic_fill(slots, heur)

            intake_complete = _slots_complete(slots)
            payload = {
                "done": True,
                "assistant_message": full_reply.strip() or "…",
                "display_name": slots.get("display_name"),
                "gender": slots.get("gender"),
                "topic": slots.get("topic"),
                "intake_complete": intake_complete,
            }
            yield f"data: {json.dumps(payload)}\n\n"
        except HTTPException as he:
            detail = he.detail
            err = detail if isinstance(detail, str) else str(detail)
            yield f"data: {json.dumps({'error': err})}\n\n"
        except ChatMessageRejected as e:
            yield f"data: {json.dumps({'error': e.reason})}\n\n"
        except Exception:
            logger.exception("[onboarding_intake] stream failure lang=%s", body.language)
            yield f"data: {json.dumps({'error': 'intake_stream_failed'})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/intake/turn", response_model=OnboardingIntakeResponse)
@limiter.limit("40/minute")
async def onboarding_intake_turn(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    body = await _load_onboarding_intake_request(request)

    msgs = _sanitize_transcript(body)
    prompt_known = _known_slots_for_llm_prompt(body.known_slots, msgs)
    sys = _build_reply_system_prompt(body.language, body.seed_display_name, prompt_known)
    lc_messages: list = [SystemMessage(content=sys)]
    lc_messages.extend(_history_to_lc(msgs))
    if msgs:
        lc_messages.append(_turn_constraint_message(prompt_known))
    else:
        lc_messages.append(
            HumanMessage(
                content=(
                    "[Bootstrap — no user reply yet.] Opening only; ask how they wish to be called."
                )
            )
        )

    try:
        llm = get_azure_chat_llm_4o_mini()
        structured_llm = llm.with_structured_output(
            _StructuredTurn,
            method="function_calling",
            include_raw=True,
        )
        packed = await structured_llm.ainvoke(lc_messages)
        parsed = packed.get("parsed")
        if parsed is None:
            logger.warning("[onboarding_intake] structured parse missing raw=%s", packed.get("raw"))
            raise HTTPException(status_code=502, detail="Intake model returned no structured payload")
        slots = _sanitize_enums_turn(parsed)
        merged = _merge_known_into_slots(
            {
                "display_name": slots["display_name"],
                "gender": slots["gender"],
                "topic": slots["topic"],
            },
            body.known_slots,
        )
        slots.update(merged)
        intake_complete = _slots_complete(slots)
        return OnboardingIntakeResponse(
            assistant_message=slots["assistant_message"],
            display_name=slots["display_name"],
            gender=slots["gender"],
            topic=slots["topic"],
            intake_complete=intake_complete,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("[onboarding_intake] LLM failure user_lang=%s", body.language)
        raise HTTPException(status_code=502, detail="Intake assistant temporarily unavailable") from None
