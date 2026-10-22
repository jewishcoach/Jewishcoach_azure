from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db, release_db_connection, utc_now
from ..models import ToolResponse, Conversation, Message, User
from ..dependencies import get_current_user
from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, List
from datetime import datetime
import logging
from ..bsd_v2.single_agent_coach import handle_conversation, _check_gate_met
from ..bsd_v2.stage_tool_triggers import resolve_post_turn_tool_call, mark_trait_picker_sent, mark_matzui_summary_sent
from ..bsd_v2.onboarding_topics_context import inject_onboarding_topics_into_state
from ..security.chat_input import ChatMessageRejected, sanitize_chat_message
from ..api.chat_v2 import save_v2_state, build_stage_complete_payload, strip_question_before_card

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])

import re
import unicodedata

def _is_gibberish(text: str) -> bool:
    """Detect obviously nonsensical text in tool submissions."""
    if not text or not isinstance(text, str):
        return False
    s = text.strip()
    if len(s) < 2:
        return True
    letters = re.sub(r'[\s\d\W_]+', '', unicodedata.normalize('NFC', s))
    if len(letters) < 2:
        return True
    if len(set(letters)) == 1:
        return True
    word_chars = re.findall(r'[֐-׿a-zA-Z]{2,}', s)
    if not word_chars:
        return True
    return False


_REQUEST_FLOOR_HE = {"pattern": ("הדפוס", "שהוא", "הישן", "החדש"), "paradigm": ("הפרדיגמה", "שהיא", "הישנה", "החדשה"),
                     "stance": ("העמדה", "שהיא", "הישנה", "החדשה")}


def compose_coaching_request(data: Dict[str, Any]) -> str:
    """The booklet's complex coaching request (p.37-38), as one sentence in the client's words."""
    name, that, old_adj, new_adj = _REQUEST_FLOOR_HE.get(data.get("floor"), _REQUEST_FLOOR_HE["pattern"])
    source = ", ".join(s for s in (data.get("source") or []) if s)
    nature = ", ".join(s for s in (data.get("nature") or []) if s)
    noun = name[1:]  # "הדפוס" → "דפוס" for "מופיע הדפוס הישן שלי"
    # booklet wording (p.37-38): "אני מבקש להתאמן על הקושי להתמודד עם [תיאור הסיטואציה]"
    parts = [f"אני מבקש/ת להתאמן על הקושי להתמודד עם {(data.get('situation') or '').strip()}"]
    if (data.get("old") or "").strip():
        parts.append(f"שכאשר מופיע{'ה' if that == 'שהיא' else ''} ה{noun} {old_adj} שלי, {that} {data['old'].strip()}")
    if source:
        parts.append(f"אפעל מתוך המקור שלי, שהוא {source}")
    if nature:
        parts.append(f"ומתוך הטבע שלי, שהוא {nature}")
    if (data.get("new") or "").strip():
        parts.append(f"ומתוך ה{noun} {new_adj} שבחרתי, {that} {data['new'].strip()}")
    parts.append(f"כדי שהתוצאה שאשיג תהיה: {(data.get('result') or '').strip()}")
    return ", ".join(p.rstrip(".,") for p in parts) + "."


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
    collected_data: Dict[str, Any] | None = None
    suggestions: list[str] = []
    stage_complete: Dict[str, Any] | None = None

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
    if not summary:
        summary = f"[הגשת כלי: {request.tool_type}]"
    try:
        summary = sanitize_chat_message(summary)
    except ChatMessageRejected as e:
        logger.warning("[Tools] Tool summary rejected: %s", e.reason)
        summary = f"[הגשת כלי: {request.tool_type}]"
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
    stage_complete_payload: Dict[str, Any] | None = None

    # Inject structured tool output into V2 state and run an immediate coach turn.
    if conversation.v2_state and isinstance(conversation.v2_state, dict):
        try:
            v2_state = dict(conversation.v2_state)
            state_version = conversation.v2_state_version or 0
            prev_step = v2_state.get("current_step", "S0")

            # Validate text quality in tool submissions — reject gibberish
            _text_fields_to_check = {
                "gap_card": ["gap_name"],
                "comparison_card": ["action_desired", "emotion_desired", "thought_desired"],
                "sentence_builder": ["paradigm"],
                "declaration_card": ["renewal"],
                "commitment_card": ["commitment", "result"],
            }
            fields_to_check = _text_fields_to_check.get(request.tool_type, [])
            for field in fields_to_check:
                val = request.data.get(field, "")
                if isinstance(val, str) and _is_gibberish(val):
                    logger.warning(f"[Tools] Gibberish detected in {request.tool_type}.{field}: '{val[:30]}'")
                    raise HTTPException(
                        status_code=422,
                        detail={"error": "gibberish", "field": field,
                                "message": "התשובה לא ברורה — נסה לנסח אחרת"}
                    )

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
                    cd["gap_belief"] = request.data["belief"]
                if request.data.get("opportunity") is not None:
                    if "opportunity" not in moves:
                        moves.append("opportunity")
                    opp = request.data["opportunity"]
                    if isinstance(opp, dict):
                        cd["gap_opportunity"] = opp.get("what", "כן") if opp.get("has") else "לא"
                    else:
                        cd["gap_opportunity"] = str(opp)
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
                renewal_parts = [f"העמדה החדשה שבחרתי: {request.data['renewal']}" if request.data.get("renewal") else ""]
                if request.data.get("next_action"):
                    renewal_parts.append(f"מה אעשה אחרת: {request.data['next_action']}")
                cd["renewal"] = ". ".join(p.rstrip(".") for p in renewal_parts if p)
                # Kept separately to prefill the coaching-request card (new stance / new pattern)
                cd["renewal_belief"] = request.data.get("renewal", "")
                cd["new_action"] = request.data.get("next_action", "")
                v2_state["collected_data"] = cd

            elif request.tool_type == "commitment_card":
                cd = dict(v2_state.get("collected_data") or {})
                if request.data.get("floor"):  # בקשה לאימון (booklet p.37-38)
                    cd["commitment"] = compose_coaching_request(request.data)
                    cd["coaching_request"] = {k: request.data.get(k) for k in
                                              ("floor", "situation", "old", "source", "nature", "new", "result")}
                else:  # legacy commitment card (open sessions from before the redesign)
                    parts = [request.data.get("commitment", "")]
                    if request.data.get("when"):
                        parts.append(f"מתי: {request.data['when']}")
                    if request.data.get("where_who"):
                        parts.append(f"איפה/מול מי: {request.data['where_who']}")
                    cd["commitment"] = ". ".join(p.rstrip(".") for p in parts if p) + "."
                v2_state["collected_data"] = cd

            if summary:
                language = v2_state.get("language", "he")
                inject_onboarding_topics_into_state(v2_state, user.preferences or {}, language)
                v2_state["_tool_just_submitted"] = request.tool_type
                user_gender = getattr(user, "gender", None) or None
                # Release the pooled connection during the LLM call. The submission + summary rows are kept out
                # of the session meanwhile so they are still committed atomically with the coach reply.
                pending = [o for o in (tool_response, system_message) if o in db.new]
                can_release = set(db.new) == set(pending) and not db.dirty and not db.deleted
                if can_release:
                    for o in pending:
                        db.expunge(o)
                    release_db_connection(db)
                try:
                    coach_message, updated_state = await handle_conversation(
                        user_message=summary,
                        state=v2_state,
                        language=language,
                        user_gender=user_gender,
                        conversation_id=conversation_id,
                    )
                finally:
                    if can_release:
                        for o in pending:
                            db.add(o)

                current_step = updated_state.get("current_step")
                saturation_score = float(updated_state.get("saturation_score", 0.0))

                # V3 S2: reflecting the event is method, but a sentence that ticks off the gate conditions
                # ("רגע ברור בזמן, עם בן הזוג, ומגע ישיר") leaks the internal check (judge: 5/11 runs) — drop it.
                if updated_state.get("ux_version", 2) >= 3 and request.tool_type == "event_form" and coach_message:
                    kept = [s for s in re.split(r"(?<=[.!?])\s+|\n+", coach_message)
                            if not (re.search(r"מגע", s) and re.search(r"זמן|מתי", s))]
                    cleaned = "\n".join(s for s in kept if s.strip())
                    if cleaned and cleaned != coach_message:
                        logger.info("[Tools] S2: dropped gate-checklist sentence from coach reflection")
                        coach_message = cleaned
                        msgs = updated_state.get("messages") or []
                        if msgs and msgs[-1].get("sender") == "coach":
                            msgs[-1]["content"] = coach_message

                # V3: after the client confirmed the מצוי card, the coach's only job is the one-sentence bridge to the
                # רצוי card. The model re-summarized the just-confirmed מצוי in 7/11 judged runs despite the prompt —
                # so the bridge is fixed text (also stored in state history).
                if (updated_state.get("ux_version", 2) >= 3 and request.tool_type == "matzui_summary" and language == "he"
                        and current_step == "S6" and coach_message):
                    coach_message = "עכשיו נדמיין איך היית רוצה שזה ייראה באותו רגע."
                    msgs = updated_state.get("messages") or []
                    if msgs and msgs[-1].get("sender") == "coach":
                        msgs[-1]["content"] = coach_message

                # Deterministic gate check: backend is the authority on step advancement.
                # Suppress when stage_ready_to_complete — let frontend stage-complete screen handle it.
                last_tool_msg = (updated_state.get("messages") or [{}])[-1] if updated_state.get("messages") else {}
                tool_stage_completing = (last_tool_msg.get("internal_state") or {}).get("stage_ready_to_complete", False)
                cd = updated_state.get("collected_data") or {}
                ux_version = updated_state.get("ux_version", 2)
                # V3: handle_conversation already applied the (V3) gate — a second pass would double-hop
                gate_next = None if ux_version >= 3 else _check_gate_met(current_step, cd)
                gate_advanced = False
                if gate_next and current_step != gate_next and not tool_stage_completing:
                    logger.info(f"[Tools] Gate auto-advance: {current_step}→{gate_next} (gate met after {request.tool_type} submission)")
                    updated_state["current_step"] = gate_next
                    current_step = gate_next
                    gate_advanced = True
                elif gate_next and tool_stage_completing:
                    logger.info(f"[Tools] Gate met {current_step}→{gate_next} but stage_ready_to_complete — deferring")

                coach_db_msg = None
                if coach_message:
                    coach_db_msg = Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=coach_message,
                        timestamp=utc_now(),
                    )
                    db.add(coach_db_msg)

                # Check for deferred tool from a previous gate advance
                tool_call = updated_state.pop("_deferred_tool", None)
                if tool_call:
                    logger.info(f"[Tools] Firing deferred tool: {tool_call.get('tool_type')}")
                if not tool_call:
                    tool_call = resolve_post_turn_tool_call(prev_step, updated_state, ux_version=ux_version, from_tool_submission=request.tool_type)
                    # Defer tool when gate just advanced — let coach's question land first
                    if tool_call and gate_advanced:
                        logger.info(f"[Tools] Deferring tool {tool_call['tool_type']} — gate just advanced {current_step}")
                        updated_state["_deferred_tool"] = tool_call
                        tool_call = None
                if tool_call and tool_call.get("tool_type") in ("trait_picker", "trait_card_builder"):
                    mark_trait_picker_sent(updated_state)
                if tool_call and tool_call.get("tool_type") == "matzui_summary":
                    mark_matzui_summary_sent(updated_state)

                # A card can be the step that ends a macro-stage (e.g. declaration_card, commitment_card)
                stage_complete_payload = await build_stage_complete_payload(updated_state, current_step, language)
                if ux_version >= 3 and (tool_call or stage_complete_payload) and coach_message:
                    stripped = strip_question_before_card(updated_state, coach_message)
                    if stripped != coach_message and coach_db_msg is not None:
                        coach_db_msg.content = stripped
                        coach_message = stripped

                save_v2_state(conversation_id, updated_state, db, expected_version=state_version, commit=False)
            else:
                save_v2_state(conversation_id, v2_state, db, expected_version=state_version, commit=False)

            logger.info(f"[Tools] Processed {request.tool_type} submission in V2 state for conv {conversation_id}")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"[Tools] Could not process tool submission in V2 state: {e}")

    db.commit()
    db.refresh(tool_response)

    # Extract collected_data from updated state for frontend sidebar
    result_collected_data = None
    if conversation.v2_state and isinstance(conversation.v2_state, dict):
        cd = conversation.v2_state.get("collected_data")
        if cd and isinstance(cd, dict):
            result_collected_data = {k: v for k, v in cd.items() if v and v != [] and v != {}}

    result_suggestions = []
    if conversation.v2_state and isinstance(conversation.v2_state, dict):
        result_suggestions = conversation.v2_state.pop("_suggestions", [])

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
        collected_data=result_collected_data,
        suggestions=result_suggestions,
        stage_complete=stage_complete_payload,
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

    elif tool_type in ("trait_picker", "trait_card_builder"):
        # Support both old keys (source_traits/nature_traits) and new keys (source_forces/nature_forces)
        source = data.get("source_forces") or data.get("source_traits") or []
        nature = data.get("nature_forces") or data.get("nature_traits") or []

        summary = "💎 **כוחות מקור וטבע (כמ\"ז) - התשובות שלי:**\n\n"

        if source:
            summary += "**כוחות מקור (אור, ערכים, שליחות):**\n"
            for trait in source:
                summary += f"- {trait}\n"

        if nature:
            summary += "\n**כוחות טבע (תכונות ונטיות טבעיות):**\n"
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
            belief_he = {"yes": "כן", "no": "לא", "unsure": "לא בטוח"}.get(belief, belief)
            parts.append(f"אמונה בשינוי: {belief_he}")
        if isinstance(opp, dict) and opp:  # legacy cards only — the gap card no longer asks it
            parts.append(f"הזדמנות: {opp.get('what', 'כן')}" if opp.get("has") else "הזדמנות: לא מזהה כרגע")
        elif opp and not isinstance(opp, dict):
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
            parts.append(f"העמדה החדשה שאני בוחר: {renewal}")
        if action:
            parts.append(f"מה אעשה אחרת: {action}")
        if data.get("feels_right") is not None:
            parts.append(f"מרגיש לי נכון: {'כן' if data['feels_right'] else 'עדיין לא'}")
        return ". ".join(parts) if parts else ""

    elif tool_type == "commitment_card" and data.get("floor"):
        return f"הבקשה שלי לאימון: {compose_coaching_request(data)}"

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
