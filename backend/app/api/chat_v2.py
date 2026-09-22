"""
BSD V2 Chat API Endpoint

Side-by-side with V1 - experimental single-agent architecture.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Literal
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
from ..bsd_v2.single_agent_coach import handle_conversation, warm_prompt_cache
from ..bsd_v2.stage_tool_triggers import resolve_post_turn_tool_call, mark_trait_picker_sent, mark_matzui_summary_sent
from ..bsd_v2.state_schema_v2 import create_initial_state
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
from ..database import get_db
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
                del msgs[i]["internal_state"]

    # Hard cap on total messages
    if len(msgs) > MAX_STATE_MESSAGES:
        state["messages"] = msgs[-TRIM_KEEP_RECENT:]


def save_v2_state(conversation_id: int, state: Dict[str, Any], db: Session, expected_version: int | None = None) -> None:
    """
    Save V2 state to database with optimistic locking.
    If expected_version is provided, the save fails with 409 if the DB version
    has changed since load (another request wrote in between).
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
    asyncio.create_task(warm_prompt_cache(language=lang, steps=("S0", "S1")))
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
        user_gender = getattr(current_user, "gender", None) or None
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

        # Save state
        t5 = time.time()
        logger.debug(
            "[BSD V2 API] Saving state: step=%s, messages=%s",
            updated_state["current_step"],
            len(updated_state.get("messages", [])),
        )
        save_v2_state(body.conversation_id, updated_state, db, expected_version=state_version)
        state_version += 1
        t6 = time.time()
        logger.debug("[PERF API] Save state to DB: %.0fms", (t6 - t5) * 1000)
        logger.debug("[BSD V2 API] State saved successfully")
        
        # Also save messages to DB (for compatibility with UI)
        t7 = time.time()
        from app.database import utc_now
        
        # Save user message
        user_msg = Message(
            conversation_id=body.conversation_id,
            role="user",
            content=safe_message,
            timestamp=utc_now()
        )
        db.add(user_msg)
        
        # Save coach message (meta.phase for smart scroll in frontend)
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
        t8 = time.time()
        logger.debug("[PERF API] Save messages to DB: %.0fms", (t8 - t7) * 1000)

        # Same as V1: smart title after 4th user message (was missing on V2-only traffic)
        try_autotitle_conversation(db, body.conversation_id, body.language or "he")
        
        # Interactive tools: S11 on entry; S12 deferred (booklet order — see stage_tool_triggers).
        tool_call = resolve_post_turn_tool_call(prev_step, updated_state, ux_version=ux_version)
        if tool_call and tool_call.get("tool_type") in ("trait_picker", "trait_card_builder"):
            mark_trait_picker_sent(updated_state)
            save_v2_state(body.conversation_id, updated_state, db, expected_version=state_version)
            state_version += 1
        if tool_call and tool_call.get("tool_type") == "matzui_summary":
            mark_matzui_summary_sent(updated_state)
            save_v2_state(body.conversation_id, updated_state, db, expected_version=state_version)
            state_version += 1
        if tool_call:
            logger.debug(
                "[BSD V2 API] tool_call: %s (step %s→%s, ux_v%s)",
                tool_call["tool_type"],
                prev_step,
                updated_state.get("current_step"),
                ux_version,
            )

        # UX V2/V3: detect macro-stage completion signal
        stage_complete_payload = None
        ux_v2_or_v3 = int(request.headers.get("x-ux-version", "1") or "1") >= 2
        if ux_v2_or_v3:
            last_msg = updated_state.get("messages", [{}])[-1] if updated_state.get("messages") else {}
            last_internal = last_msg.get("internal_state") or {}
            if last_internal.get("stage_ready_to_complete"):
                current_step = updated_state.get("current_step", "S0")
                current_macro_id = step_to_macro_stage(current_step)
                if current_macro_id:
                    end_step = MACRO_STAGE_END_STEPS.get(current_macro_id)
                    step_num = int(current_step.replace("S", ""))
                    end_num = int(end_step.replace("S", "")) if end_step else -1
                    if step_num >= end_num:
                        try:
                            summary = await generate_stage_summary(
                                updated_state, current_macro_id, body.language
                            )
                            stage_complete_payload = summary.model_dump()
                        except Exception:
                            logger.exception("[BSD V2 API] Failed to generate stage summary on completion")

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
        coach_msg, updated_state = await handle_conversation(
            "אני מוכן להתחיל" if body.language == "he" else "I'm ready to start",
            state_fresh,
            language=body.language,
            user_gender=user_gender,
            conversation_id=body.conversation_id,
        )
        updated_state.pop("_stage_opening", None)
        save_v2_state(body.conversation_id, updated_state, db, expected_version=ver_fresh)
        opening_message = coach_msg
    except Exception as e:
        logger.warning("[BSD V2 API] Failed to generate stage opening message: %s", e)

    return {
        "ok": True,
        "stage": body.macro_stage,
        "current_step": first_step,
        "opening_message": opening_message,
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

