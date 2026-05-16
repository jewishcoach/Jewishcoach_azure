"""
LLM-powered first-entry onboarding: streaming coach replies + structured slot extraction.

- POST /intake/stream — SSE: token chunks then final JSON with slots (recommended UX).
- POST /intake/turn — single structured response (fallback / simple clients).
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field, model_validator

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

_GOALS = frozenset({"peace", "confidence", "knowSelf", "pattern"})
_EXPERIENCE = frozenset({"coached", "new", "self", "unsure"})
_PACES = frozenset({"gentle", "weekly", "immersive", "focused"})


class OnboardingChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=MAX_CHAT_MESSAGE_CHARS)


class OnboardingIntakeRequest(BaseModel):
    language: str = Field(default="he", max_length=16)
    messages: list[OnboardingChatMessage] = Field(default_factory=list, max_length=48)
    seed_display_name: Optional[str] = Field(default=None, max_length=120)

    @model_validator(mode="before")
    @classmethod
    def coerce_raw_body(cls, data: Any) -> Any:
        """Avoid 422 from minor client/schema drift (null content, wrong role casing, odd language types)."""
        if not isinstance(data, dict):
            return {"language": "he", "messages": [], "seed_display_name": None}

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

        return out


class OnboardingIntakeResponse(BaseModel):
    assistant_message: str
    display_name: Optional[str] = None
    gender: Optional[Literal["male", "female"]] = None
    goal: Optional[str] = None
    experience: Optional[str] = None
    pace: Optional[str] = None
    intake_complete: bool = False


class _StructuredTurn(BaseModel):
    assistant_message: str = Field(..., max_length=4000)
    display_name: Optional[str] = Field(default=None, max_length=80)
    gender: Optional[Literal["male", "female"]] = None
    goal: Optional[str] = None
    experience: Optional[str] = None
    pace: Optional[str] = None


class _SlotsOnly(BaseModel):
    """Post-reply extraction — cumulative slots from full transcript + latest coach text."""

    display_name: Optional[str] = Field(default=None, max_length=80)
    gender: Optional[Literal["male", "female"]] = None
    goal: Optional[str] = None
    experience: Optional[str] = None
    pace: Optional[str] = None


def _slug(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    t = str(s).strip()
    return t or None


def _normalize_slots(
    display_name: Optional[str],
    gender: Optional[str],
    goal: Optional[str],
    experience: Optional[str],
    pace: Optional[str],
) -> dict[str, Any]:
    g = _slug(goal)
    if g is not None and g not in _GOALS:
        g = None
    e = _slug(experience)
    if e is not None and e not in _EXPERIENCE:
        e = None
    p = _slug(pace)
    if p is not None and p not in _PACES:
        p = None
    gen = gender
    if gen not in ("male", "female", None):
        gen = None
    name = _slug(display_name)
    return {
        "display_name": name,
        "gender": gen,
        "goal": g,
        "experience": e,
        "pace": p,
    }


def _sanitize_enums_turn(parsed: _StructuredTurn) -> dict[str, Any]:
    base = _normalize_slots(parsed.display_name, parsed.gender, parsed.goal, parsed.experience, parsed.pace)
    base["assistant_message"] = (parsed.assistant_message or "").strip() or "…"
    return base


def _sanitize_enums_slots(parsed: _SlotsOnly) -> dict[str, Any]:
    return _normalize_slots(parsed.display_name, parsed.gender, parsed.goal, parsed.experience, parsed.pace)


def _slots_complete(slots: dict[str, Any]) -> bool:
    return bool(
        slots.get("display_name")
        and slots.get("gender") in ("male", "female")
        and slots.get("goal") in _GOALS
        and slots.get("experience") in _EXPERIENCE
        and slots.get("pace") in _PACES
    )


def _build_reply_system_prompt(language: str, seed_display_name: Optional[str]) -> str:
    lang = (language or "he").lower()
    primary = "Hebrew" if lang.startswith("he") else "English"
    hint = ""
    if seed_display_name and seed_display_name.strip():
        hint = (
            f"\nA signup hint suggests this name (confirm naturally, user may correct): "
            f"{seed_display_name.strip()[:80]}\n"
        )
    return f"""You are the BSD Jewish Coach intake assistant — warm, concise, respectful.
Write ONLY in {primary} (the user's locale).

Have a SHORT natural conversation (often 4–8 user turns) to learn:
1) What to call them (display name)
2) Gender for Hebrew grammar — politely ask; only male or female in our product
3) Main coaching goal (inner peace / confidence / self-knowledge / overcoming a pattern)
4) Past coaching experience level
5) Preferred pacing (gentle, weekly rhythm, deeper dives, short focused bursts)

Rules:
- One focus per message when possible; if they answer several things at once, acknowledge warmly.
- Never output JSON, bullet lists of internal codes, or markup — natural prose only.
- Keep replies brief (usually 1–3 short paragraphs).
- When you already know everything needed, warmly recap and invite them to continue into the app.
{hint}
"""


def _build_extract_system_prompt() -> str:
    return """You extract onboarding slots from a coaching intake transcript (Hebrew and/or English).

Return CUMULATIVE best-known values from the ENTIRE transcript plus the coach's latest reply:
- display_name: short name to call the user; null if unknown.
- gender: only "male" or "female"; null if not stated.
- goal: exactly one of peace, confidence, knowSelf, pattern — or null if unknown.
  peace=inner calm/peace; confidence=self-confidence; knowSelf=know myself; pattern=habit/pattern to change.
- experience: exactly one of coached, new, self, unsure — or null.
  coached=worked with coach before; new=new to coaching; self=likes self-guided; unsure=unsure.
- pace: exactly one of gentle, weekly, immersive, focused — or null.

Use null whenever uncertain. Do not invent."""


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


def _lc_messages_for_reply(language: str, seed: Optional[str], msgs: list[OnboardingChatMessage]) -> list:
    sys = _build_reply_system_prompt(language, seed)
    lc_messages: list = [SystemMessage(content=sys)]
    lc_messages.extend(_history_to_lc(msgs))
    if not msgs:
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
        return _normalize_slots(None, None, None, None, None)
    return _sanitize_enums_slots(parsed)


async def _stream_reply_tokens(lc_messages: list) -> AsyncIterator[str]:
    llm = get_azure_chat_llm_4o_mini()
    async for chunk in llm.astream(lc_messages):
        piece = _chunk_text(chunk)
        if piece:
            yield piece


@router.post("/intake/stream")
@limiter.limit("40/minute")
async def onboarding_intake_stream(
    request: Request,
    body: OnboardingIntakeRequest,
    current_user: User = Depends(get_current_user),
):
    """SSE stream: many `data: {\"content\":\"...\"}` lines, then `data: {\"done\":true,...slots}`"""
    _ = current_user

    async def event_gen() -> AsyncIterator[str]:
        try:
            msgs = _sanitize_transcript(body)
            lc_messages = _lc_messages_for_reply(body.language, body.seed_display_name, msgs)
            full_reply = ""
            async for piece in _stream_reply_tokens(lc_messages):
                full_reply += piece
                yield f"data: {json.dumps({'content': piece})}\n\n"

            slots = await _extract_slots(msgs, full_reply)
            intake_complete = _slots_complete(slots)
            payload = {
                "done": True,
                "assistant_message": full_reply.strip() or "…",
                "display_name": slots.get("display_name"),
                "gender": slots.get("gender"),
                "goal": slots.get("goal"),
                "experience": slots.get("experience"),
                "pace": slots.get("pace"),
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
    body: OnboardingIntakeRequest,
    current_user: User = Depends(get_current_user),
):
    _ = current_user

    msgs = _sanitize_transcript(body)
    sys = _build_reply_system_prompt(body.language, body.seed_display_name)
    lc_messages: list = [SystemMessage(content=sys)]
    lc_messages.extend(_history_to_lc(msgs))

    if not msgs:
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
        intake_complete = _slots_complete(slots)
        return OnboardingIntakeResponse(
            assistant_message=slots["assistant_message"],
            display_name=slots["display_name"],
            gender=slots["gender"],
            goal=slots["goal"],
            experience=slots["experience"],
            pace=slots["pace"],
            intake_complete=intake_complete,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("[onboarding_intake] LLM failure user_lang=%s", body.language)
        raise HTTPException(status_code=502, detail="Intake assistant temporarily unavailable") from None
