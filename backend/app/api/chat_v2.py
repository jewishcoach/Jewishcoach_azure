"""
BSD V2 Chat API Endpoint

Side-by-side with V1 - experimental single-agent architecture.
"""

import asyncio
import json
import logging
import re
import time
from typing import Dict, Any, Literal, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..dependencies import get_current_user, get_current_admin_user
from ..client_safe import client_error_detail
from ..security.chat_input import (
    MAX_CHAT_MESSAGE_CHARS,
    ChatMessageRejected,
    sanitize_chat_message,
)
from ..middleware.usage_limiter import require_message_quota
from ..bsd_v2.single_agent_coach import handle_conversation, warm_prompt_cache, _check_gate_met
from ..bsd_v2.stage_tool_triggers import resolve_post_turn_tool_call, mark_trait_picker_sent, mark_matzui_summary_sent
from ..bsd_v2.state_schema_v2 import create_initial_state, add_message
from ..bsd_v2.safety_check import screen_message
from ..bsd_v2.station_checkpoint import ensure_training_started_at, apply_station_intent
from ..bsd_v2.onboarding_topics_context import inject_onboarding_topics_into_state
from ..bsd_v2.stage_intro_schema import (
    MACRO_STAGE_IDS,
    MACRO_STAGE_END_STEPS,
    MACRO_STAGE_START_STEPS,
    get_macro_stage,
    next_macro_stage,
    step_to_macro_stage,
)
from ..bsd_v2.stage_intro_generator import (
    generate_stage_intro,
    generate_stage_summary,
    format_intro_answers_as_context,
)
from ..database import SessionLocal, get_db, release_db_connection
from ..limiter import limiter
from ..models import User, Conversation as ConversationModel, Message
from ..routers.chat import try_autotitle_conversation
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat/v2", tags=["BSD V2"])


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ══════════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_CHAT_MESSAGE_CHARS)
    conversation_id: int
    language: str = "he"


class ChatResponse(BaseModel):
    coach_message: str
    conversation_id: int
    current_step: str
    saturation_score: float
    suggestions: list[str] = []  # Quick-reply options for structured chat flow
    collected_data: dict | None = None  # Progressive insights (topic, emotions, event, etc.)
    tool_call: dict | None = None  # Interactive tool to activate in InsightHub
    station_checkpoint: dict | None = None  # Sticky mission card + Insights (V2 stations)
    stage_complete: dict | None = None  # Macro-stage completion signal (UX V2)
    is_error: bool = False  # True when response is a fallback due to server error
    safety: str | None = None  # Set when coach_message is a safety response (possible_risk | imminent)


class StationIntentRequest(BaseModel):
    conversation_id: int
    intent: Literal["pause_here", "continue_coaching"]


# ══════════════════════════════════════════════════════════════════════════════
# STATE PERSISTENCE (Simple JSON in DB)
# ══════════════════════════════════════════════════════════════════════════════


def _get_conversation_or_404(
    conversation_id: int,
    user_id: int,
    db: Session,
) -> ConversationModel:
    """
    Load conversation and verify ownership.
    Raises HTTPException 404 if not found or not owned (avoids information disclosure).
    """
    conv = db.query(ConversationModel).filter(
        ConversationModel.id == conversation_id,
        ConversationModel.user_id == user_id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


# Strong refs to fire-and-forget tasks (the event loop only keeps weak references)
_background_tasks: set = set()


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def _autotitle_in_thread(conversation_id: int, language: str) -> None:
    """Title generation uses a SYNC OpenAI client — run it off the event loop with its own session, after the
    response, so a slow/429-retrying call can't freeze the worker or hold a pooled connection."""
    db = SessionLocal()
    try:
        try_autotitle_conversation(db, conversation_id, language)
    except Exception:
        logger.exception("[BSD V2 API] autotitle failed for conv %s", conversation_id)
    finally:
        db.close()


def strip_question_before_card(state: Dict[str, Any], coach_message: str) -> str:
    """V3: when a card or the stage-complete screen follows the coach message, drop its
    closing question — the user can't answer it in chat (the card replaces the input).
    Keeps the state's stored coach message in sync."""
    if not coach_message or "?" not in coach_message.rstrip()[-3:]:
        return coach_message
    def _drop_trailing_questions(parts: list) -> list:
        while parts and "?" in parts[-1].rstrip()[-3:]:
            parts = parts[:-1]
        return parts

    paragraphs = _drop_trailing_questions([p for p in coach_message.strip().split("\n") if p.strip()])
    if paragraphs:
        stripped = "\n".join(paragraphs).strip()
    else:
        sentences = _drop_trailing_questions(re.split(r"(?<=[.!?])\s+", coach_message.strip()))
        stripped = " ".join(sentences).strip()
    if not stripped:
        return coach_message
    msgs = state.get("messages") or []
    if msgs and msgs[-1].get("sender") == "coach" and msgs[-1].get("content") == coach_message:
        msgs[-1]["content"] = stripped
    return stripped


_HE_WORD = re.compile(r"[\u0590-\u05FF]{3,}")


def drop_repeated_trigger_reflection(state: Dict[str, Any], coach_message: str, user_message: str) -> str:
    """V3 S9→S11: the coach reflects the client's trigger answer almost verbatim and then repeats it as the first
    link of the chain ("אז כש... נדלקת האמונה...") — the same content twice (judge: 10/11 runs; prompt fixes
    failed). Keep the chain, drop earlier paragraphs that mostly re-state the client's answer."""
    paragraphs = [p for p in (coach_message or "").split("\n") if p.strip()]
    chain_idx = next((i for i, p in enumerate(paragraphs)
                      if i > 0 and re.match(r"(אז|אם (אני )?נחבר|אם (אני )?מחבר|בוא נחבר)", p.strip())
                      and re.search(r"נדלק|מדליק", p)), None)
    if chain_idx is None:
        return coach_message
    user_words = set(_HE_WORD.findall(user_message or ""))

    def _restates_answer(p: str) -> bool:
        # A mini-chain before the chain ("...מדליק את האמונה...") is the same content; word overlap catches
        # near-verbatim restatements (Hebrew inflection אותי→אותך lowers it, hence both checks)
        if re.search(r"מדליק|נדלק|כפתור", p):
            return True
        words = set(_HE_WORD.findall(p))
        return len(user_words) >= 4 and bool(words) and len(words & user_words) / len(words) >= 0.35

    kept = [p for i, p in enumerate(paragraphs) if i >= chain_idx or not _restates_answer(p)]
    if len(kept) == len(paragraphs):
        return coach_message
    cleaned = "\n\n".join(kept)
    msgs = state.get("messages") or []
    if msgs and msgs[-1].get("sender") == "coach" and msgs[-1].get("content") == coach_message:
        msgs[-1]["content"] = cleaned
    logger.info("[BSD V2 API] S9: dropped %d paragraph(s) repeating the trigger before the chain", len(paragraphs) - len(kept))
    return cleaned


async def build_stage_complete_payload(state: Dict[str, Any], step: str, language: str) -> Optional[Dict[str, Any]]:
    """Stage summary payload when the last coach turn signaled stage_ready_to_complete
    at (or past) the end step of its macro-stage; None otherwise."""
    last_msg = state.get("messages", [{}])[-1] if state.get("messages") else {}
    if not (last_msg.get("internal_state") or {}).get("stage_ready_to_complete"):
        return None
    completing_macro_id = step_to_macro_stage(step)
    if not completing_macro_id:
        return None
    end_step = MACRO_STAGE_END_STEPS.get(completing_macro_id)
    end_num = int(end_step.replace("S", "")) if end_step else -1
    if int(step.replace("S", "")) < end_num:
        return None
    try:
        summary = await generate_stage_summary(state, completing_macro_id, language)
        return summary.model_dump()
    except Exception:
        logger.exception("[BSD V2 API] Failed to generate stage summary on completion")
        return None


def load_v2_state(conversation_id: int, db: Session) -> tuple[Dict[str, Any], int]:
    """
    Load V2 state from database.
    Returns (state_dict, version) for optimistic locking.
    """
    conv = db.query(ConversationModel).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    version = conv.v2_state_version or 0

    if conv.v2_state and isinstance(conv.v2_state, dict):
        logger.debug(f"[BSD V2 API] Loaded existing state with {len(conv.v2_state.get('messages', []))} messages, version={version}")
        return conv.v2_state, version

    logger.debug(f"[BSD V2 API] Creating new state for conversation {conversation_id}")
    return create_initial_state(
        conversation_id=str(conversation_id),
        user_id=str(conv.user_id),
        language="he"
    ), version


MAX_STATE_MESSAGES = 40
TRIM_KEEP_RECENT = 20


def _prune_state_messages(state: Dict[str, Any]) -> None:
    """
    Trim the in-state message list to prevent unbounded JSON growth.
    Full messages are already persisted in the Message table.
    - Strip internal_state from all but the last 6 coach messages.
    - If total messages exceed MAX_STATE_MESSAGES, keep only the most recent TRIM_KEEP_RECENT.
    """
    msgs = state.get("messages")
    if not msgs:
        return

    # Strip internal_state from older messages (biggest space savings)
    coach_count_from_end = 0
    for i in range(len(msgs) - 1, -1, -1):
        if msgs[i].get("sender") == "coach" or msgs[i].get("role") == "assistant":
            coach_count_from_end += 1
            if coach_count_from_end > 6 and "internal_state" in msgs[i]:
                # keep the step tag: the V3 gates/notes count which questions were asked in the current step
                step = (msgs[i]["internal_state"] or {}).get("current_step")
                if step:
                    msgs[i]["internal_state"] = {"current_step": step}
                else:
                    del msgs[i]["internal_state"]

    # Hard cap on total messages
    if len(msgs) > MAX_STATE_MESSAGES:
        state["messages"] = msgs[-TRIM_KEEP_RECENT:]


def save_v2_state(
    conversation_id: int,
    state: Dict[str, Any],
    db: Session,
    expected_version: int | None = None,
    commit: bool = True,
) -> None:
    """
    Save V2 state to database with optimistic locking.
    If expected_version is provided, the save fails with 409 if the DB version
    has changed since load (another request wrote in between).

    When commit=False, stages changes on the session without committing.
    The caller is responsible for calling db.commit() (atomic transaction pattern).
    """
    conv = db.query(ConversationModel).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if expected_version is not None:
        current_version = conv.v2_state_version or 0
        if current_version != expected_version:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Conversation was updated by another request. Please retry.",
            )

    _prune_state_messages(state)

    conv.v2_state = state
    conv.current_phase = state.get("current_step", "S0")
    conv.v2_state_version = (conv.v2_state_version or 0) + 1

    if commit:
        db.commit()
    logger.debug(f"[BSD V2 API] Saved state with {len(state.get('messages', []))} messages, version={conv.v2_state_version}")


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/warmup")
@limiter.limit("120/minute")
async def warmup_cache(request: Request, language: str = "he"):
    """
    Pre-warm Azure prompt cache for new conversations.
    Call when user opens/creates a conversation - before first message.
    No auth required (best-effort shared cache); rate-limited by IP behind proxy.

    Returns immediately; warm-up runs in background.
    """
    import asyncio

    lang = (language or "he").lower().strip()
    if not lang.startswith("en"):
        lang = "he"
    _spawn(warm_prompt_cache(language=lang, steps=("S0", "S1")))
    return {"status": "warmup_started", "language": lang}


@router.post("/station-intent")
def station_intent_v2(
    body: StationIntentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Persist user choice after a station checkpoint (pause vs continue).
    Shapes the next coach turn via session_flow flags (no LLM call).
    """
    _get_conversation_or_404(body.conversation_id, current_user.id, db)
    state, ver = load_v2_state(body.conversation_id, db)
    apply_station_intent(state, body.intent)
    save_v2_state(body.conversation_id, state, db, expected_version=ver)
    return {"ok": True}


@router.post("/message", response_model=ChatResponse)
@limiter.limit("60/minute")
async def send_message_v2(
    request: Request,
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_message_quota),
):
    """
    BSD V2 chat endpoint - single-agent conversational coach.
    
    Unlike V1's multi-layer architecture, V2 uses a single LLM call
    with rich context and clear guidance for natural conversation.
    
    Usage:
        POST /api/chat/v2/message
        {
            "message": "זוגיות",
            "conversation_id": 123,
            "language": "he"
        }
    
    Returns:
        {
            "coach_message": "זוגיות, אוקיי. ספר לי יותר...",
            "conversation_id": 123,
            "current_step": "S1",
            "saturation_score": 0.5
        }
    """
    state: Dict[str, Any] = {}
    safe_message: str | None = None
    try:
        safe_message = sanitize_chat_message(body.message)
        api_start = time.time()

        logger.debug(
            "[BSD V2 API] request user=%s conv=%s msg_len=%s",
            current_user.id,
            body.conversation_id,
            len(body.message or ""),
        )

        logger.debug("[BSD V2 API] User %s sent message to conv %s", current_user.id, body.conversation_id)
        
        # Verify conversation ownership before any load/save
        _get_conversation_or_404(body.conversation_id, current_user.id, db)
        
        # Load state
        t1 = time.time()
        state, state_version = load_v2_state(body.conversation_id, db)
        ensure_training_started_at(state)
        inject_onboarding_topics_into_state(state, current_user.preferences or {}, body.language)

        # Dedup: if the last message in state is this exact user message, skip processing.
        # This catches retries after partial commit (500 retry with already-saved state).
        last_msgs = state.get("messages") or []
        if last_msgs and last_msgs[-1].get("sender") == "user" and last_msgs[-1].get("content") == safe_message:
            logger.warning("[BSD V2 API] Duplicate message detected (retry after partial commit), returning last coach response")
            last_coach = next((m for m in reversed(last_msgs) if m.get("sender") == "coach"), None)
            coach_text = last_coach["content"] if last_coach else ""
            return ChatResponse(
                coach_message=coach_text,
                conversation_id=body.conversation_id,
                current_step=state.get("current_step", "S0"),
                saturation_score=float(state.get("saturation_score", 0)),
                collected_data=state.get("collected_data"),
            )

        # Don't hold a pooled DB connection across the LLM calls below (read ORM attributes first)
        user_gender = getattr(current_user, "gender", None) or None
        release_db_connection(db)

        # Safety screen BEFORE the coach: a risk statement gets a check-in, not the next coaching step
        safety_result = await screen_message(safe_message, state, request.headers.get("x-user-timezone"))
        if safety_result.intercept:
            from app.database import utc_now
            add_message(state, "user", safe_message)
            add_message(state, "coach", safety_result.message)
            save_v2_state(body.conversation_id, state, db, expected_version=state_version, commit=False)
            db.add(Message(conversation_id=body.conversation_id, role="user", content=safe_message, timestamp=utc_now()))
            db.add(Message(conversation_id=body.conversation_id, role="assistant", content=safety_result.message,
                           timestamp=utc_now(), meta={"phase": state.get("current_step", "S0"), "safety": safety_result.level}))
            db.commit()
            logger.warning("[BSD V2 API] Safety response (%s) for conv %s", safety_result.level, body.conversation_id)
            return ChatResponse(
                coach_message=safety_result.message,
                conversation_id=body.conversation_id,
                current_step=state.get("current_step", "S0"),
                saturation_score=float(state.get("saturation_score", 0)),
                collected_data=state.get("collected_data"),
                safety=safety_result.level,
            )

        # Snapshot previous step BEFORE any V3 skip or handle_conversation.
        prev_step = state.get("current_step", "S0")

        # V3: store ux_version in state so prompts and coach logic can branch
        ux_version = int(request.headers.get("x-ux-version", "2") or "2")
        if ux_version >= 3:
            state["ux_version"] = ux_version
            # Skip S0-S1: if conversation is new (S0), jump to S2
            if state.get("current_step") in ("S0", "S1"):
                state["current_step"] = "S2"
                # Set topic from onboarding context if available
                onboarding_ctx = state.get("stage_intro_context", {}).get("identification", "")
                if onboarding_ctx and not state["collected_data"].get("topic"):
                    state["collected_data"]["topic"] = onboarding_ctx[:200]
                logger.info("[BSD V2 API] V3: skipped S0-S1, starting at S2")

        t2 = time.time()
        logger.debug("[PERF API] Load state from DB: %.0fms", (t2 - t1) * 1000)
        logger.debug(
            "[BSD V2 API] Loaded state: step=%s, messages=%s",
            state["current_step"],
            len(state.get("messages", [])),
        )

        # Handle conversation (pass user gender from dashboard for אתה/את)
        t3 = time.time()
        coach_message, updated_state = await handle_conversation(
            user_message=safe_message,
            state=state,
            language=body.language,
            user_gender=user_gender,
            conversation_id=body.conversation_id,
        )
        t4 = time.time()
        logger.debug("[PERF API] handle_conversation: %.0fms", (t4 - t3) * 1000)

        station_checkpoint = updated_state.pop("last_station_checkpoint_api", None)

        # --- Atomic transaction: stage all DB changes, commit once at the end ---
        from app.database import utc_now

        # Deterministic gate check: the backend is the AUTHORITY on step advancement.
        # If collected_data satisfies the gate, advance — regardless of what the LLM decided.
        # The LLM focuses on coaching quality; the backend manages flow control.
        # BUT: skip when stage_ready_to_complete is signaled — the frontend
        # stage-complete screen must show before crossing macro boundaries.
        last_msg_for_gate = (updated_state.get("messages") or [{}])[-1] if updated_state.get("messages") else {}
        stage_completing = (last_msg_for_gate.get("internal_state") or {}).get("stage_ready_to_complete", False)
        pre_gate_step = updated_state.get("current_step", "S0")
        cur_step = pre_gate_step
        cd = updated_state.get("collected_data") or {}
        # V3: handle_conversation already applied the (V3) gate — a second pass would double-hop
        gate_next = None if ux_version >= 3 else _check_gate_met(cur_step, cd)
        gate_advanced = False
        if gate_next and cur_step != gate_next and not stage_completing:
            logger.info(f"[BSD V2 API] Gate auto-advance: {cur_step}→{gate_next} (collected_data satisfies gate)")
            updated_state["current_step"] = gate_next
            gate_advanced = True
        elif gate_next and stage_completing:
            logger.info(f"[BSD V2 API] Gate met {cur_step}→{gate_next} but stage_ready_to_complete — deferring to frontend")

        # Check for deferred tool from previous turn's gate advance
        tool_call = updated_state.pop("_deferred_tool", None)
        if tool_call:
            logger.info(f"[BSD V2 API] Firing deferred tool: {tool_call.get('tool_type')}")

        if not tool_call:
            tool_call = resolve_post_turn_tool_call(prev_step, updated_state, ux_version=ux_version)
            # When gate just advanced in this chat turn, defer the tool so the
            # coach's message (often a confirmation question) lands first.
            # The deferred tool fires on the NEXT turn.
            if tool_call and gate_advanced:
                logger.info(
                    f"[BSD V2 API] Deferring tool {tool_call['tool_type']} — gate just advanced {cur_step}→{gate_next}"
                )
                updated_state["_deferred_tool"] = tool_call
                tool_call = None

        if tool_call and tool_call.get("tool_type") in ("trait_picker", "trait_card_builder"):
            mark_trait_picker_sent(updated_state)
        if tool_call and tool_call.get("tool_type") == "matzui_summary":
            mark_matzui_summary_sent(updated_state)
        if tool_call:
            logger.debug(
                "[BSD V2 API] tool_call: %s (step %s→%s, ux_v%s)",
                tool_call["tool_type"],
                prev_step,
                updated_state.get("current_step"),
                ux_version,
            )

        # UX V2/V3: detect macro-stage completion signal
        # Use pre_gate_step (step BEFORE any gate auto-advance) to identify
        # the correct macro-stage — gate may have already pushed into the next one.
        stage_complete_payload = None
        ux_v2_or_v3 = int(request.headers.get("x-ux-version", "1") or "1") >= 2
        if ux_v2_or_v3:
            stage_complete_payload = await build_stage_complete_payload(updated_state, pre_gate_step, body.language)
        if ux_version >= 3 and (tool_call or stage_complete_payload):
            coach_message = strip_question_before_card(updated_state, coach_message)
        if ux_version >= 3 and prev_step in ("S9", "S10") and updated_state.get("current_step") == "S11":
            coach_message = drop_repeated_trigger_reflection(updated_state, coach_message, safe_message)

        # --- SINGLE ATOMIC COMMIT: save everything together ---
        t5 = time.time()
        save_v2_state(body.conversation_id, updated_state, db, expected_version=state_version, commit=False)
        state_version += 1

        # Save user + coach messages to Messages table (for UI compatibility)
        user_msg = Message(
            conversation_id=body.conversation_id,
            role="user",
            content=safe_message,
            timestamp=utc_now()
        )
        db.add(user_msg)
        coach_meta: Dict[str, Any] = {"phase": updated_state["current_step"]}
        if station_checkpoint:
            coach_meta["station_checkpoint"] = station_checkpoint
        coach_msg = Message(
            conversation_id=body.conversation_id,
            role="assistant",
            content=coach_message,
            timestamp=utc_now(),
            meta=coach_meta,
        )
        db.add(coach_msg)

        db.commit()
        t6 = time.time()
        logger.debug("[PERF API] Atomic commit (state + messages): %.0fms", (t6 - t5) * 1000)

        # Auto-title runs AFTER the atomic commit (non-critical, can fail independently)
        _spawn(asyncio.to_thread(_autotitle_in_thread, body.conversation_id, body.language or "he"))

        suggestions = updated_state.pop("_suggestions", [])
        collected_data = updated_state.get("collected_data")
        # Filter out empty values for cleaner frontend payload
        if collected_data and isinstance(collected_data, dict):
            collected_data = {k: v for k, v in collected_data.items() if v and v != [] and v != {}}
        else:
            collected_data = None

        response = ChatResponse(
            coach_message=coach_message,
            conversation_id=body.conversation_id,
            current_step=updated_state["current_step"],
            saturation_score=updated_state["saturation_score"],
            suggestions=suggestions,
            collected_data=collected_data if collected_data else None,
            tool_call=tool_call,
            station_checkpoint=station_checkpoint,
            stage_complete=stage_complete_payload,
        )
        
        api_end = time.time()
        api_total_ms = (api_end - api_start) * 1000

        logger.debug(
            "[BSD V2 API] response coach_len=%s step=%s total_ms=%.0f",
            len(coach_message),
            updated_state["current_step"],
            api_total_ms,
        )
        logger.debug("[PERF API] TOTAL API TIME: %.0fms (%.1fs)", api_total_ms, api_total_ms / 1000)

        return response

    except HTTPException:
        # Re-raise HTTPException (404, 401, etc.) without wrapping in 500
        raise
    except ChatMessageRejected as e:
        raise HTTPException(
            status_code=400,
            detail={"error": e.reason, "message": "Invalid message content"},
        )
    except Exception as e:
        db.rollback()
        logger.exception("[BSD V2 API] Error")
        try:
            from ..bsd_v2.error_buffer import capture_error
            capture_error("chat_v2_api", e, {"conv_id": body.conversation_id})
        except Exception:
            pass
        fallback_he = "הייתה לי בעיה טכנית. תוכל לחזור על זה?"
        fallback_en = "I had a technical issue. Could you try again?"
        fallback_msg = fallback_he if (body.language or "he") == "he" else fallback_en
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content=ChatResponse(
                coach_message=fallback_msg,
                conversation_id=body.conversation_id,
                current_step=state.get("current_step", "S1"),
                saturation_score=state.get("saturation_score", 0.3),
                station_checkpoint=None,
                is_error=True,
            ).model_dump(),
        )


# ══════════════════════════════════════════════════════════════════════════════
# LOAD CONVERSATION (for resuming past sessions)
# ══════════════════════════════════════════════════════════════════════════════

class ConversationLoadResponse(BaseModel):
    conversation_id: int
    current_step: str
    messages: list[dict]
    collected_data: dict | None = None
    personal_statements: dict | None = None
    updated_at: str | None = None


@router.get("/conversation/{conversation_id}")
async def load_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Load a V2 conversation for resuming in the frontend."""
    conv = _get_conversation_or_404(conversation_id, current_user.id, db)
    state = conv.v2_state or {}
    raw_messages = state.get("messages", [])

    frontend_messages = []
    for msg in raw_messages:
        sender = msg.get("sender") or msg.get("role", "")
        content = msg.get("content", "")
        if not content:
            continue
        role = "assistant" if sender in ("coach", "assistant") else "user"
        frontend_messages.append({
            "id": f"{'a' if role == 'assistant' else 'u'}-{len(frontend_messages)}",
            "role": role,
            "content": content,
        })

    collected_data = state.get("collected_data")
    if collected_data and isinstance(collected_data, dict):
        collected_data = {k: v for k, v in collected_data.items() if v and v != [] and v != {}}
    else:
        collected_data = None

    personal_statements = state.get("personal_statements")
    updated_at = None
    if hasattr(conv, 'updated_at') and conv.updated_at:
        updated_at = conv.updated_at.isoformat()
    elif conv.created_at:
        updated_at = conv.created_at.isoformat()

    return ConversationLoadResponse(
        conversation_id=conversation_id,
        current_step=state.get("current_step", "S0"),
        messages=frontend_messages,
        collected_data=collected_data,
        personal_statements=personal_statements if personal_statements else None,
        updated_at=updated_at,
    )


# ══════════════════════════════════════════════════════════════════════════════
# DEBUG: Recent errors (in-memory, last 20)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/debug/errors")
async def get_recent_errors_debug(
    _admin: User = Depends(get_current_admin_user),
):
    """Return recent BSD V2 errors for debugging. Admin only."""
    try:
        from ..bsd_v2.error_buffer import get_recent_errors
        return {"errors": get_recent_errors(), "count": len(get_recent_errors())}
    except Exception as e:
        return {
            "errors": [],
            "count": 0,
            "error": client_error_detail("failed", e),
        }


# ══════════════════════════════════════════════════════════════════════════════
# DEBUG: Export last conversation (for analyzing coach behavior)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/debug/last-conversation")
async def get_last_conversation_debug(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Return the user's most recent V2 conversation in full (messages + state).
    Admin-only export for coach behavior analysis.
    """
    conv = db.query(ConversationModel).filter(
        ConversationModel.user_id == current_user.id,
        ConversationModel.v2_state.isnot(None)
    ).order_by(ConversationModel.created_at.desc()).first()
    
    if not conv or not conv.v2_state:
        return {"message": "No V2 conversation found", "conversation_id": None}
    
    state = conv.v2_state
    messages = state.get("messages", [])
    
    # Build readable transcript
    transcript = []
    for m in messages:
        role = m.get("sender") or m.get("role", "?")
        content = (m.get("content") or "").strip()
        if content:
            transcript.append({"role": role, "content": content})
    
    return {
        "conversation_id": conv.id,
        "title": conv.title,
        "current_step": state.get("current_step"),
        "saturation_score": state.get("saturation_score"),
        "collected_data": state.get("collected_data"),
        "transcript": transcript,
        "message_count": len(messages),
    }


@router.get("/debug/conversation/{conversation_id}")
async def get_conversation_debug(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Export a specific conversation for debugging (same format as last-conversation). Admin only."""
    conv = _get_conversation_or_404(conversation_id, current_user.id, db)
    if not conv.v2_state:
        return {"message": "Not a V2 conversation (no v2_state)", "conversation_id": conversation_id}
    
    state = conv.v2_state
    messages = state.get("messages", [])
    transcript = []
    for m in messages:
        role = m.get("sender") or m.get("role", "?")
        content = (m.get("content") or "").strip()
        if content:
            transcript.append({"role": role, "content": content})
    
    return {
        "conversation_id": conv.id,
        "title": conv.title,
        "current_step": state.get("current_step"),
        "saturation_score": state.get("saturation_score"),
        "collected_data": state.get("collected_data"),
        "transcript": transcript,
        "message_count": len(messages),
    }


# ══════════════════════════════════════════════════════════════════════════════
# INSIGHTS ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/conversations/{conversation_id}/insights")
async def get_conversation_insights_v2(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get accumulated cognitive data (insights) for a V2 conversation.
    
    Returns structured data including:
    - Current stage
    - Collected data (from collected_data in state)
    - Saturation score
    - Message count
    
    Usage:
        GET /api/chat/v2/conversations/123/insights
    
    Returns:
        {
            "current_stage": "S3",
            "saturation_score": 0.75,
            "cognitive_data": {
                "topic": "...",
                "event": "...",
                "emotions": [...],
                ...
            },
            "metrics": {
                "message_count": 15,
                "turns_in_current_stage": 5
            }
        }
    """
    try:
        logger.debug("[BSD V2 API] Getting insights for conversation %s", conversation_id)
        
        # Verify conversation ownership
        conv = _get_conversation_or_404(conversation_id, current_user.id, db)
        
        # Load V2 state
        state, _ver = load_v2_state(conversation_id, db)
        
        # Extract insights from state
        current_stage = state.get("current_step", "S0")
        saturation_score = state.get("saturation_score", 0.0)
        collected_data = state.get("collected_data", {})
        messages = state.get("messages", [])
        
        # Count turns in current stage
        turns_in_current_stage = sum(
            1 for msg in messages 
            if msg.get("role") == "user" and msg.get("metadata", {}).get("step") == current_stage
        )
        
        user_msg_total = sum(
            1 for msg in messages 
            if isinstance(msg, dict) and (msg.get("role") or msg.get("sender")) == "user"
        )

        return {
            "current_stage": current_stage,
            "saturation_score": saturation_score,
            "cognitive_data": collected_data,
            "metrics": {
                "message_count": user_msg_total,
                "turns_in_current_stage": turns_in_current_stage
            },
            "updated_at": (conv_updated := getattr(conv, 'updated_at', None) or conv.created_at) and conv_updated.isoformat() or None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[BSD V2 API] Error getting insights")
        raise HTTPException(
            status_code=500,
            detail=client_error_detail("Unable to load insights", e),
        )


# ══════════════════════════════════════════════════════════════════════════════
# STAGE INTRO (UX V2 — structured macro-stage transitions)
# ══════════════════════════════════════════════════════════════════════════════


class StageIntroRequest(BaseModel):
    conversation_id: int
    target_macro_stage: str = Field(..., description="Target macro-stage id: identification, discovery, kamaz, choice, vision")
    language: str = "he"


class StageIntroAnswerRequest(BaseModel):
    conversation_id: int
    macro_stage: str
    answers: Dict[str, list] = Field(..., description="question_id -> list of selected option_ids")
    language: str = "he"


@router.post("/stage-intro")
@limiter.limit("20/minute")
async def get_stage_intro(
    request: Request,
    body: StageIntroRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate contextual intro questions for the next macro-stage.
    Called after user sees stage-complete card and taps "Continue".

    Returns LLM-generated questions with contextual answer options.
    """
    if body.target_macro_stage not in MACRO_STAGE_IDS:
        raise HTTPException(status_code=400, detail=f"Invalid macro-stage: {body.target_macro_stage}")

    _get_conversation_or_404(body.conversation_id, current_user.id, db)
    state, ver = load_v2_state(body.conversation_id, db)
    release_db_connection(db)

    try:
        intro_payload = await generate_stage_intro(
            state=state,
            target_macro_id=body.target_macro_stage,
            language=body.language,
        )
    except Exception as e:
        logger.exception("[BSD V2 API] Failed to generate stage intro for %s", body.target_macro_stage)
        raise HTTPException(
            status_code=500,
            detail=client_error_detail("Failed to generate intro questions", e),
        )

    state["pending_stage_intro"] = intro_payload.model_dump()
    save_v2_state(body.conversation_id, state, db, expected_version=ver)

    return intro_payload.model_dump()


@router.post("/stage-intro-answers")
@limiter.limit("20/minute")
async def submit_stage_intro_answers(
    request: Request,
    body: StageIntroAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit user's answers to the structured intro questions.
    Advances the conversation to the new macro-stage and injects
    the answers as context for the next free-chat phase.
    """
    if body.macro_stage not in MACRO_STAGE_IDS:
        raise HTTPException(status_code=400, detail=f"Invalid macro-stage: {body.macro_stage}")

    _get_conversation_or_404(body.conversation_id, current_user.id, db)
    state, ver = load_v2_state(body.conversation_id, db)

    pending = state.get("pending_stage_intro")
    if not pending:
        raise HTTPException(status_code=400, detail="No pending stage intro to answer")

    questions = pending.get("questions", [])
    context_str = format_intro_answers_as_context(
        answers=body.answers,
        questions=[q if isinstance(q, dict) else q for q in questions],
        language=body.language,
    )

    if "stage_intro_context" not in state:
        state["stage_intro_context"] = {}
    state["stage_intro_context"][body.macro_stage] = context_str

    first_step = MACRO_STAGE_START_STEPS.get(body.macro_stage, "S0")
    state["current_step"] = first_step
    state["saturation_score"] = 0.0

    state.pop("pending_stage_intro", None)

    state["_stage_opening"] = True
    save_v2_state(body.conversation_id, state, db, expected_version=ver)

    # Generate coach opening message for the new stage
    opening_message = None
    try:
        user_gender = getattr(current_user, "gender", None) or None
        state_fresh, ver_fresh = load_v2_state(body.conversation_id, db)
        release_db_connection(db)
        coach_msg, updated_state = await handle_conversation(
            "אני מוכן להתחיל" if body.language == "he" else "I'm ready to start",
            state_fresh,
            language=body.language,
            user_gender=user_gender,
            conversation_id=body.conversation_id,
        )
        updated_state.pop("_stage_opening", None)

        # V3: resolve tool_call for the new stage opening
        ux_version = int(request.headers.get("x-ux-version", "2") or "2")
        opening_tool_call = resolve_post_turn_tool_call(
            prev_step="__stage_intro__",
            state=updated_state,
            ux_version=ux_version,
        )
        if opening_tool_call and opening_tool_call.get("tool_type") in ("trait_picker", "trait_card_builder"):
            mark_trait_picker_sent(updated_state)
        if ux_version >= 3 and opening_tool_call:
            coach_msg = strip_question_before_card(updated_state, coach_msg)

        save_v2_state(body.conversation_id, updated_state, db, expected_version=ver_fresh)
        opening_message = coach_msg
    except Exception as e:
        logger.warning("[BSD V2 API] Failed to generate stage opening message: %s", e)
        opening_tool_call = None

    return {
        "ok": True,
        "stage": body.macro_stage,
        "current_step": first_step,
        "opening_message": opening_message,
        "tool_call": opening_tool_call if ux_version >= 3 else None,
    }


@router.post("/stage-summary")
@limiter.limit("20/minute")
async def get_stage_summary(
    request: Request,
    body: StageIntroRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the summary for a completed macro-stage.
    Called when stage_complete signal is received, to populate the completion card.
    (target_macro_stage here means the stage that just completed)
    """
    _get_conversation_or_404(body.conversation_id, current_user.id, db)
    state, _ver = load_v2_state(body.conversation_id, db)
    release_db_connection(db)

    try:
        summary = await generate_stage_summary(
            state=state,
            completed_macro_id=body.target_macro_stage,
            language=body.language,
        )
    except Exception as e:
        logger.exception("[BSD V2 API] Failed to generate stage summary for %s", body.target_macro_stage)
        raise HTTPException(
            status_code=500,
            detail=client_error_detail("Failed to generate stage summary", e),
        )

    return summary.model_dump()


# ══════════════════════════════════════════════════════════════════════════════
# PERSONAL STATEMENT (saved per macro-stage)
# ══════════════════════════════════════════════════════════════════════════════


class PersonalStatementRequest(BaseModel):
    stage_id: str
    statement: str = Field(..., min_length=1, max_length=500)


@router.post("/conversations/{conversation_id}/statement")
async def save_personal_statement(
    conversation_id: int,
    body: PersonalStatementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save the user's personal insight statement for a completed macro-stage."""
    _get_conversation_or_404(conversation_id, current_user.id, db)
    state, ver = load_v2_state(conversation_id, db)

    if "personal_statements" not in state:
        state["personal_statements"] = {}
    state["personal_statements"][body.stage_id] = body.statement

    save_v2_state(conversation_id, state, db, expected_version=ver)
    return {"ok": True}

