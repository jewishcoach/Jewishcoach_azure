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


# Mirrors chat_v2 stage-entry tool triggers so submit can chain naturally.
_STAGE_TOOL_TRIGGERS: dict[str, dict] = {
    "S11": {
        "type": "tool",
        "tool_type": "profit_loss",
        "title_he": "טבלת רווח והפסד",
        "title_en": "Gain / Loss Table",
        "instruction_he": "מה אתה מרוויח מהדפוס הזה? ומה אתה מפסיד? מלא את הטבלה.",
        "instruction_en": "What do you gain from this pattern? And what do you lose? Fill in the table.",
    },
    "S12": {
        "type": "tool",
        "tool_type": "trait_picker",
        "title_he": "כוחות מקור וטבע (כמ\"ז)",
        "title_en": "Source & Nature Forces (KMZ)",
        "instruction_he": "מהם הערכים והאמונות שמניעים אותך (מקור)? ומהן היכולות והכישרונות הטבעיים שלך (טבע)?",
        "instruction_en": "What are the values and beliefs that drive you (source)? And what are your natural abilities and talents (nature)?",
    },
}


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

            elif request.tool_type == "trait_picker":
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

            if summary:
                language = v2_state.get("language", "he")
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

                if current_step and current_step != prev_step and current_step in _STAGE_TOOL_TRIGGERS:
                    tool_call = _STAGE_TOOL_TRIGGERS[current_step]
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

    # Default: just stringify the data
    return f"[הגשת כלי: {tool_type}]"
