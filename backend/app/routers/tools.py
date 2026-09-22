from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db, utc_now
from ..models import ToolResponse, Conversation, Message, User
from ..dependencies import get_current_user
from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, List
from datetime import datetime
import logging
from ..bsd_v2.single_agent_coach import handle_conversation
from ..bsd_v2.stage_tool_triggers import resolve_post_turn_tool_call, mark_trait_picker_sent, mark_matzui_summary_sent
from ..bsd_v2.onboarding_topics_context import inject_onboarding_topics_into_state
from ..security.chat_input import ChatMessageRejected, sanitize_chat_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])


class ToolSubmitRequest(BaseModel):
    tool_type: str
    data: Dict[str, Any]


class ToolResponseModel(BaseModel):
    id: int
    conversation_id: int
    tool_type: str
    data: Dict[str, Any]
    created_at: datetime
    coach_message: str | None = None
    current_step: str | None = None
    saturation_score: float | None = None
    tool_call: Dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


@router.post("/{conversation_id}/submit", response_model=ToolResponseModel)
async def submit_tool_response(
    conversation_id: int,
    request: ToolSubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit tool response data (e.g., Profit & Loss table, Trait Picker results)
    and optionally generate an immediate coach continuation.
    """
    # Verify conversation ownership
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=403, detail="Conversation not found or unauthorized")

    # Save tool response
    tool_response = ToolResponse(
        conversation_id=conversation_id,
        tool_type=request.tool_type,
        data=request.data,
        created_at=utc_now()
    )
    db.add(tool_response)

    # Create a summary message so the messages table stays in sync.
    summary = _generate_tool_summary(request.tool_type, request.data)
    if summary:
        try:
            summary = sanitize_chat_message(summary)
        except ChatMessageRejected as e:
            logger.warning("[Tools] Tool summary rejected: %s", e.reason)
            summary = ""
    if summary:
        system_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=summary,
            timestamp=utc_now(),
            meta={"tool_submission": True, "tool_type": request.tool_type}
        )
        db.add(system_message)

    coach_message: str | None = None
    current_step: str | None = None
    saturation_score: float | None = None
    tool_call: Dict[str, Any] | None = None

    # Inject structured tool output into V2 state and run an immediate coach turn.
    if conversation.v2_state and isinstance(conversation.v2_state, dict):
        try:
            v2_state = dict(conversation.v2_state)
            prev_step = v2_state.get("current_step", "S0")

            # Persist structured data directly into collected_data for insights panel
            if request.tool_type == "profit_loss":
                cd = dict(v2_state.get("collected_data") or {})
                stance = dict(cd.get("stance") or {})
                gains = request.data.get("gains", [])
                losses = request.data.get("losses", [])
                if gains:
                    stance["gains"] = gains
                if losses:
                    stance["losses"] = losses
                cd["stance"] = stance
                v2_state["collected_data"] = cd

            elif request.tool_type in ("trait_picker", "trait_card_builder"):
                cd = dict(v2_state.get("collected_data") or {})
                forces = dict(cd.get("forces") or {})
                source = request.data.get("source_forces") or request.data.get("source_traits") or []
                nature = request.data.get("nature_forces") or request.data.get("nature_traits") or []
                if source:
                    forces["source"] = source
                if nature:
                    forces["nature"] = nature
                cd["forces"] = forces
                v2_state["collected_data"] = cd

            elif request.tool_type == "event_form":
                cd = dict(v2_state.get("collected_data") or {})
                parts = []
                if request.data.get("when"):
                    parts.append(request.data["when"])
                if request.data.get("with_whom"):
                    parts.append(f"עם {request.data['with_whom']}")
                if request.data.get("what_happened"):
                    parts.append(request.data["what_happened"])
                cd["event_description"] = " — ".join(parts) if parts else ""
                v2_state["collected_data"] = cd

            elif request.tool_type == "emotion_selector":
                cd = dict(v2_state.get("collected_data") or {})
                cd["emotions"] = request.data.get("emotions", [])
                v2_state["collected_data"] = cd

            elif request.tool_type == "action_field":
                cd = dict(v2_state.get("collected_data") or {})
                cd["action_actual"] = request.data.get("action_actual", "")
                v2_state["collected_data"] = cd

            elif request.tool_type == "comparison_card":
                cd = dict(v2_state.get("collected_data") or {})
                cd["action_desired"] = request.data.get("action_desired", "")
                cd["emotion_desired"] = request.data.get("emotion_desired", "")
                cd["thought_desired"] = request.data.get("thought_desired", "")
                v2_state["collected_data"] = cd

            elif request.tool_type == "gap_card":
                cd = dict(v2_state.get("collected_data") or {})
                cd["gap_name"] = request.data.get("gap_name", "")
                cd["gap_score"] = str(request.data.get("gap_score", ""))
                moves = list(cd.get("gap_booklet_moves") or [])
                if request.data.get("belief") is not None:
                    if "belief" not in moves:
                        moves.append("belief")
                if request.data.get("opportunity") is not None:
                    if "opportunity" not in moves:
                        moves.append("opportunity")
                cd["gap_booklet_moves"] = moves
                v2_state["collected_data"] = cd

            elif request.tool_type == "sentence_builder":
                cd = dict(v2_state.get("collected_data") or {})
                cd["paradigm"] = request.data.get("paradigm", "")
                stance = dict(cd.get("stance") or {})
                if request.data.get("reality_belief"):
                    stance["reality_belief"] = request.data["reality_belief"]
                cd["stance"] = stance
                v2_state["collected_data"] = cd

            elif request.tool_type == "balance_scale":
                cd = dict(v2_state.get("collected_data") or {})
                stance = dict(cd.get("stance") or {})
                gains = request.data.get("gains", [])
                losses = request.data.get("losses", [])
                if gains:
                    stance["gains"] = gains
                if losses:
                    stance["losses"] = losses
                cd["stance"] = stance
                v2_state["collected_data"] = cd

            elif request.tool_type == "declaration_card":
                cd = dict(v2_state.get("collected_data") or {})
                cd["renewal"] = request.data.get("renewal", "")
                v2_state["collected_data"] = cd

            elif request.tool_type == "commitment_card":
                cd = dict(v2_state.get("collected_data") or {})
                parts = []
                if request.data.get("commitment"):
                    parts.append(request.data["commitment"])
                if request.data.get("when"):
                    parts.append(f"מתי: {request.data['when']}")
                if request.data.get("where_who"):
                    parts.append(f"איפה/מול מי: {request.data['where_who']}")
                cd["commitment"] = " | ".join(parts) if parts else ""
                v2_state["collected_data"] = cd

            if summary:
                language = v2_state.get("language", "he")
                inject_onboarding_topics_into_state(v2_state, user.preferences or {}, language)
                user_gender = getattr(user, "gender", None) or None
                coach_message, updated_state = await handle_conversation(
                    user_message=summary,
                    state=v2_state,
                    language=language,
                    user_gender=user_gender,
                    conversation_id=conversation_id,
                )
                conversation.v2_state = updated_state
                conversation.current_phase = updated_state.get("current_step", conversation.current_phase)

                current_step = updated_state.get("current_step")
                saturation_score = float(updated_state.get("saturation_score", 0.0))

                if coach_message:
                    db.add(Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=coach_message,
                        timestamp=utc_now(),
                    ))

                ux_version = v2_state.get("ux_version", 2)
                tool_call = resolve_post_turn_tool_call(prev_step, updated_state, ux_version=ux_version)
                if tool_call and tool_call.get("tool_type") in ("trait_picker", "trait_card_builder"):
                    mark_trait_picker_sent(updated_state)
                    conversation.v2_state = updated_state
                if tool_call and tool_call.get("tool_type") == "matzui_summary":
                    mark_matzui_summary_sent(updated_state)
                    conversation.v2_state = updated_state
            else:
                conversation.v2_state = v2_state

            logger.info(f"[Tools] Processed {request.tool_type} submission in V2 state for conv {conversation_id}")
        except Exception as e:
            logger.warning(f"[Tools] Could not process tool submission in V2 state: {e}")

    db.commit()
    db.refresh(tool_response)

    return ToolResponseModel(
        id=tool_response.id,
        conversation_id=tool_response.conversation_id,
        tool_type=tool_response.tool_type,
        data=tool_response.data,
        created_at=tool_response.created_at,
        coach_message=coach_message,
        current_step=current_step,
        saturation_score=saturation_score,
        tool_call=tool_call,
    )


@router.get("/{conversation_id}/history", response_model=List[ToolResponseModel])
def get_tool_history(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all tool responses for a conversation"""
    # Verify conversation ownership
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=403, detail="Conversation not found or unauthorized")

    tool_responses = db.query(ToolResponse).filter(
        ToolResponse.conversation_id == conversation_id
    ).order_by(ToolResponse.created_at.desc()).all()

    return tool_responses


def _generate_tool_summary(tool_type: str, data: Dict[str, Any]) -> str:
    """Generate a human-readable summary of tool submission"""
    if tool_type == "profit_loss":
        gains = data.get("gains", [])
        losses = data.get("losses", [])

        summary = "📊 **טבלת רווח והפסד - התשובות שלי:**\n\n"

        if gains:
            summary += "**מה אני מרוויח:**\n"
            for gain in gains:
                summary += f"- {gain}\n"

        if losses:
            summary += "\n**מה אני מפסיד:**\n"
            for loss in losses:
                summary += f"- {loss}\n"

        return summary.strip()

    elif tool_type == "trait_picker":
        # Support both old keys (source_traits/nature_traits) and new keys (source_forces/nature_forces)
        source = data.get("source_forces") or data.get("source_traits") or []
        nature = data.get("nature_forces") or data.get("nature_traits") or []

        summary = "💎 **כוחות מקור וטבע (כמ\"ז) - התשובות שלי:**\n\n"

        if source:
            summary += "**כוחות מקור (ערכים ואמונות):**\n"
            for trait in source:
                summary += f"- {trait}\n"

        if nature:
            summary += "\n**כוחות טבע (יכולות וכישרונות):**\n"
            for trait in nature:
                summary += f"- {trait}\n"

        return summary.strip()

    elif tool_type == "vision_board_input":
        vision = data.get("vision", "")
        summary = f"🔮 **החזון שלי:**\n\n{vision}"
        return summary.strip()

    # V3 structured tools
    elif tool_type == "event_form":
        when = data.get("when", "")
        who = data.get("with_whom", "")
        what = data.get("what_happened", "")
        return f"סיפרתי על אירוע: {when} עם {who} — {what}".strip()

    elif tool_type == "emotion_selector":
        emotions = data.get("emotions", [])
        return f"הרגשות שזיהיתי: {', '.join(emotions)}" if emotions else ""

    elif tool_type == "action_field":
        action = data.get("action_actual", "")
        return f"מה שעשיתי בפועל: {action}" if action else ""

    elif tool_type == "matzui_summary":
        return "אישרתי את תמונת המצוי"

    elif tool_type == "comparison_card":
        ed = data.get("emotion_desired", "")
        td = data.get("thought_desired", "")
        ad = data.get("action_desired", "")
        parts = []
        if ed:
            parts.append(f"הייתי רוצה להרגיש: {ed}")
        if td:
            parts.append(f"הייתי רוצה לחשוב: {td}")
        if ad:
            parts.append(f"הייתי רוצה לעשות: {ad}")
        return "הרצוי שלי: " + ". ".join(parts) if parts else ""

    elif tool_type == "gap_card":
        name = data.get("gap_name", "")
        score = data.get("gap_score", "")
        belief = data.get("belief", "")
        opp = data.get("opportunity", {})
        parts = [f"הפער: {name} (ציון {score}/10)"]
        if belief:
            parts.append(f"אמונה בשינוי: {belief}")
        if isinstance(opp, dict) and opp.get("has"):
            parts.append(f"הזדמנות: {opp.get('what', 'כן')}")
        elif opp:
            parts.append(f"הזדמנות: {opp}")
        return " | ".join(parts)

    elif tool_type == "sentence_builder":
        paradigm = data.get("paradigm", "")
        belief = data.get("reality_belief", "")
        parts = []
        if paradigm:
            parts.append(f"ככה זה אצלי: {paradigm}")
        if belief:
            parts.append(f"האמונה: {belief}")
        return ". ".join(parts) if parts else ""

    elif tool_type == "balance_scale":
        gains = data.get("gains", [])
        losses = data.get("losses", [])
        parts = []
        if gains:
            parts.append(f"רווחים: {', '.join(gains)}")
        if losses:
            parts.append(f"הפסדים: {', '.join(losses)}")
        return " / ".join(parts) if parts else ""

    elif tool_type == "declaration_card":
        renewal = data.get("renewal", "")
        action = data.get("next_action", "")
        parts = []
        if renewal:
            parts.append(f"אני בוחר: {renewal}")
        if action:
            parts.append(f"מה אעשה אחרת: {action}")
        return ". ".join(parts) if parts else ""

    elif tool_type == "commitment_card":
        commitment = data.get("commitment", "")
        when = data.get("when", "")
        where_who = data.get("where_who", "")
        parts = [f"המחויבות שלי: {commitment}"]
        if when:
            parts.append(f"מתי: {when}")
        if where_who:
            parts.append(f"איפה/מול מי: {where_who}")
        return " | ".join(parts)

    # Default: just stringify the data
    return f"[הגשת כלי: {tool_type}]"
