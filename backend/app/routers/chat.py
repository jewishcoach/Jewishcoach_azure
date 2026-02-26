from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..schemas import MessageCreate, ConversationResponse
from ..models import Conversation, Message, User, ConversationFlag, BsdSessionState, BsdAuditLog
from ..bsd.engine import BsdEngine
from typing import List, Dict
from datetime import datetime
from openai import AzureOpenAI
import json
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])
bsd_engine = BsdEngine()


def _infer_topic_from_messages(messages: list) -> str:
    """
    Fallback: infer coaching topic from first user messages (like previous system).
    Used when LLM does not populate collected_data.topic in S1.
    """
    if not messages:
        return ""
    for msg in messages[:6]:
        if not isinstance(msg, dict):
            continue
        sender = msg.get("sender") or msg.get("role")
        if sender not in ("user", "human"):
            continue
        content = (msg.get("content") or "").strip()
        if not content or content.startswith("{"):
            continue
        if 5 <= len(content) <= 80:
            return content
        if len(content) > 80:
            return content[:77] + "..."
    return ""


def _v2_collected_data_to_cognitive_data(collected: dict, messages: list = None) -> dict:
    """
    Transform V2 collected_data schema to frontend CognitiveData format.
    SmartInsightsPanel expects: event_actual, gap_analysis, pattern_id, kmz_forces, etc.
    V2 has: emotions, thought, action_actual, gap_name, gap_score, pattern, forces, etc.
    """
    if not collected:
        collected = {}
    out = {}
    topic = collected.get("topic") or ""
    if topic and str(topic).strip() and topic not in ("[נושא]", "[topic]"):
        out["topic"] = str(topic).strip()
    elif messages and len(messages) >= 2:
        inferred = _infer_topic_from_messages(messages)
        if inferred:
            out["topic"] = inferred
    # event_actual: emotions_list, thought_content, action_content, action_desired, emotion_desired, thought_desired
    emotions = collected.get("emotions") or []
    thought = collected.get("thought")
    action_actual = collected.get("action_actual")
    action_desired = collected.get("action_desired")
    emotion_desired = collected.get("emotion_desired")
    thought_desired = collected.get("thought_desired")
    if emotions or thought or action_actual or action_desired or emotion_desired or thought_desired:
        out["event_actual"] = {}
        if emotions:
            out["event_actual"]["emotions_list"] = emotions if isinstance(emotions, list) else [emotions]
        if thought:
            out["event_actual"]["thought_content"] = thought
        if action_actual:
            out["event_actual"]["action_content"] = action_actual
        if action_desired:
            out["event_actual"]["action_desired"] = action_desired
    # Flat keys for HudPanel compatibility
    if emotions:
        out["emotions"] = emotions if isinstance(emotions, list) else [emotions]
    if thought:
        out["thought"] = thought
    if action_actual:
        out["action_actual"] = action_actual
    if action_desired:
        out["action_desired"] = action_desired
        if emotion_desired:
            out["event_actual"]["emotion_desired"] = emotion_desired
        if thought_desired:
            out["event_actual"]["thought_desired"] = thought_desired
    # gap_analysis + flat keys for HudPanel
    gap_name = collected.get("gap_name")
    gap_score = collected.get("gap_score")
    if gap_name is not None or gap_score is not None:
        out["gap_analysis"] = {"name": gap_name, "score": gap_score}
        if gap_name is not None:
            out["gap_name"] = gap_name
        if gap_score is not None:
            out["gap_score"] = gap_score
    # pattern_id: V2 has flat "pattern" - use as name
    pattern = collected.get("pattern")
    stance = collected.get("stance") or {}
    if not isinstance(stance, dict):
        stance = {}
    if pattern:
        paradigm = (stance.get("gains") or [""])[0] if stance.get("gains") else ""
        out["pattern_id"] = {"name": pattern, "paradigm": paradigm}
        out["pattern"] = pattern
    # being_desire: V2 has stance.gains/losses, renewal, vision - map identity from renewal
    renewal = collected.get("renewal")
    vision = collected.get("vision")
    if renewal or vision or stance.get("gains") or stance.get("losses"):
        out["being_desire"] = {"identity": renewal or vision or (stance.get("gains") or [""])[0] if stance.get("gains") else ""}
    # kmz_forces: V2 has forces.source, forces.nature
    forces = collected.get("forces") or {}
    if not isinstance(forces, dict):
        forces = {}
    if forces.get("source") or forces.get("nature"):
        out["kmz_forces"] = {
            "source_forces": forces.get("source") or [],
            "nature_forces": forces.get("nature") or []
        }
    # commitment: V2 has flat "commitment" - could be string or dict
    commitment = collected.get("commitment")
    if commitment:
        if isinstance(commitment, dict):
            out["commitment"] = commitment
        else:
            out["commitment"] = {"difficulty": str(commitment), "result": ""}
    return out

# OpenAI client for title generation
openai_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)


def generate_smart_title(content: str, language: str = "he") -> str:
    """Generate a smart, concise title from conversation content using OpenAI"""
    try:
        if language == "he":
            prompt = f"""צור כותרת קצרה ותמציתית (מקסימום 40 תווים) לשיחת אימון.
המשתמש אמר: "{content[:300]}"

צור כותרת שמתארת את הנושא המרכזי שהמשתמש רוצה לעבוד עליו.
השב רק עם הכותרת, שום דבר אחר. ללא מרכאות."""
        else:
            prompt = f"""Create a very short, concise title (max 40 characters) for a coaching conversation.
The user said: "{content[:300]}"

Generate a title that captures the main theme the user wants to work on.
Reply ONLY with the title, nothing else. No quotes."""

        response = openai_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates concise conversation titles. Be specific and capture the essence." if language == "en" else "אתה עוזר שיוצר כותרות תמציתיות לשיחות. היה ספציפי ותפוס את המהות."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more focused titles
            max_tokens=60
        )
        
        title = response.choices[0].message.content.strip()
        # Remove quotes if present
        title = title.strip('"\'„"״\'')
        # Limit length
        if len(title) > 50:
            title = title[:47] + "..."
        
        return title
    except Exception as e:
        print(f"Error generating title: {e}")
        # Fallback to simple truncation
        return (content[:40] + "...") if len(content) > 40 else content

# Background task for quality checking
async def run_quality_check(
    conversation_id: int,
    message_id: int,
    history: List[Dict],
    current_stage: str,
    latest_response: str,
    db_session: Session
):
    """
    Background task: Run LLM-as-a-Judge quality check.
    
    This runs asynchronously after the response is sent to the user,
    ensuring zero latency impact on user experience.
    """
    try:
        from ..services.auto_evaluator import QualityJudge
        
        judge = QualityJudge()
        flag_data = await judge.evaluate_response(
            conversation_history=history,
            current_stage=current_stage,
            latest_bot_response=latest_response,
            db=db_session
        )
        
        if flag_data:  # Issue detected
            flag = ConversationFlag(
                conversation_id=conversation_id,
                message_id=message_id,
                stage=current_stage,
                issue_type=flag_data["issue_type"],
                reasoning=flag_data["reasoning"],
                severity=flag_data["severity"]
            )
            db_session.add(flag)
            db_session.commit()
            print(f"🚨 Quality Flag Created: {flag_data['issue_type']} (Severity: {flag_data['severity']}) in {current_stage}")
        
    except Exception as e:
        print(f"❌ Background quality check failed: {e}")
        import traceback
        traceback.print_exc()
        # Don't crash on judge errors - just log

@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new conversation for authenticated user"""
    title = f"New Conversation - {datetime.now().strftime('%b %d')}"
    
    conversation = Conversation(
        user_id=user.id,
        title=title
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    # Pre-warm prompt cache for faster first response
    from ..bsd_v2.single_agent_coach import warm_prompt_cache
    background_tasks.add_task(warm_prompt_cache, "he", ("S0", "S1"))

    return conversation

@router.get("/conversations", response_model=List[ConversationResponse])
def get_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all conversations for the authenticated user"""
    conversations = db.query(Conversation)\
        .filter(Conversation.user_id == user.id)\
        .order_by(Conversation.created_at.desc())\
        .all()
    return conversations

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a conversation with ownership verification"""
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    
    if not conv:
        raise HTTPException(status_code=403, detail="Conversation not found or unauthorized")
    return conv

@router.get("/conversations/{conversation_id}/insights/safe")
def get_conversation_insights_safe(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get insights for a conversation, but return empty data instead of 404 if not found.
    
    This is useful for frontend components that poll insights but should handle
    deleted or non-existent conversations gracefully.
    """
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    
    if not conv:
        # Return empty structure instead of 404
        return {
            "exists": False,
            "current_stage": "S0",
            "saturation_score": 0.0,
            "cognitive_data": {},
            "metrics": {},
            "message": "Conversation not found"
        }
    
    # If conversation exists, return normal insights
    # (Use the same logic as get_conversation_insights)
    if conv.v2_state and isinstance(conv.v2_state, dict):
        try:
            state = conv.v2_state
            current_stage = state.get("current_step", "S0")
            saturation_score = state.get("saturation_score", 0.0)
            collected_data = state.get("collected_data", {})
            messages = state.get("messages", [])
            
            turns_in_current_stage = 0
            try:
                turns_in_current_stage = sum(
                    1 for msg in messages 
                    if isinstance(msg, dict) and 
                    msg.get("role") == "user" and 
                    msg.get("metadata", {}).get("step") == current_stage
                )
            except Exception as e:
                logger.warning(f"Could not count turns: {e}")
            
            # Transform V2 collected_data to frontend CognitiveData schema
            cognitive_data = _v2_collected_data_to_cognitive_data(collected_data, messages)
            logger.info(
                f"[Insights] conv={conversation_id} step={current_stage} "
                f"collected_keys={list(collected_data.keys()) if collected_data else []} "
                f"cognitive_keys={list(cognitive_data.keys()) if cognitive_data else []}"
            )
            return {
                "exists": True,
                "current_stage": current_stage,
                "saturation_score": saturation_score,
                "cognitive_data": cognitive_data,
                "metrics": {
                    "message_count": len(messages),
                    "turns_in_current_stage": turns_in_current_stage
                },
                "updated_at": (conv_updated := getattr(conv, 'updated_at', None) or conv.created_at) and conv_updated.isoformat() or None
            }
        except Exception as e:
            logger.error(f"Error extracting V2 insights: {e}")
    
    # V1 fallback
    bsd_state = db.query(BsdSessionState).filter(
        BsdSessionState.conversation_id == conversation_id
    ).first()
    
    if not bsd_state:
        return {
            "exists": True,
            "current_stage": conv.current_phase or "S0",
            "saturation_score": 0.0,
            "cognitive_data": {},
            "metrics": {
                "loop_count_in_current_stage": 0,
                "shehiya_depth_score": 0.0
            }
        }
    
    return {
        "exists": True,
        "current_stage": bsd_state.current_stage,
        "saturation_score": 0.0,
        "cognitive_data": bsd_state.cognitive_data or {},
        "metrics": bsd_state.metrics or {},
        "updated_at": bsd_state.updated_at.isoformat() if bsd_state.updated_at else None
    }


@router.get("/conversations/{conversation_id}/exists")
def check_conversation_exists(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if a conversation exists and belongs to the current user.
    
    This is a lightweight endpoint for frontend validation.
    """
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    
    return {
        "exists": conv is not None,
        "conversation_id": conversation_id
    }


@router.get("/conversations/{conversation_id}/insights")
def get_conversation_insights(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get accumulated cognitive data (insights) for a conversation.
    
    Supports both V1 (BsdSessionState) and V2 (v2_state) conversations.
    
    Returns structured data including:
    - Topic (S1)
    - Event details (S2)
    - Emotions (S3)
    - Thought (S4)
    - Action (S5)
    - Gap analysis (S6)
    - Pattern (S7)
    - Being desire (S8)
    - KaMaZ forces (S9)
    - Commitment (S10)
    
    Returns 404 if conversation doesn't exist or user doesn't have access.
    Frontend should handle this gracefully by stopping insights polling.
    """
    # Verify conversation ownership
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    
    if not conv:
        logger.warning(
            f"Insights request for non-existent conversation: "
            f"conversation_id={conversation_id}, user_id={user.id}"
        )
        raise HTTPException(
            status_code=404, 
            detail={
                "error": "conversation_not_found",
                "message": "Conversation not found or you don't have access to it",
                "conversation_id": conversation_id
            }
        )
    
    # Check if this is a V2 conversation (has v2_state)
    if conv.v2_state and isinstance(conv.v2_state, dict):
        try:
            # V2 conversation - extract insights from v2_state
            state = conv.v2_state
            current_stage = state.get("current_step", "S0")
            saturation_score = state.get("saturation_score", 0.0)
            collected_data = state.get("collected_data", {})
            messages = state.get("messages", [])
            
            # Count turns in current stage (safely handle different message structures)
            turns_in_current_stage = 0
            try:
                turns_in_current_stage = sum(
                    1 for msg in messages 
                    if isinstance(msg, dict) and 
                    msg.get("role") == "user" and 
                    msg.get("metadata", {}).get("step") == current_stage
                )
            except Exception as e:
                logger.warning(f"Could not count turns: {e}")
                turns_in_current_stage = 0
            
            cognitive_data = _v2_collected_data_to_cognitive_data(collected_data, messages)
            return {
                "current_stage": current_stage,
                "saturation_score": saturation_score,
                "cognitive_data": cognitive_data,
                "metrics": {
                    "message_count": len(messages),
                    "turns_in_current_stage": turns_in_current_stage
                },
                "updated_at": (conv_updated := getattr(conv, 'updated_at', None) or conv.created_at) and conv_updated.isoformat() or None
            }
        except Exception as e:
            logger.error(f"Error extracting V2 insights: {e}")
            # Fall through to V1 logic or return minimal data
            pass
    
    # V1 conversation - get BSD session state
    bsd_state = db.query(BsdSessionState).filter(
        BsdSessionState.conversation_id == conversation_id
    ).first()
    
    if not bsd_state:
        # No BSD state yet (conversation just started)
        return {
            "current_stage": conv.current_phase or "S0",
            "cognitive_data": {},
            "metrics": {
                "loop_count_in_current_stage": 0,
                "shehiya_depth_score": 0.0
            }
        }
    
    return {
        "current_stage": bsd_state.current_stage,
        "cognitive_data": bsd_state.cognitive_data or {},
        "metrics": bsd_state.metrics or {},
        "updated_at": bsd_state.updated_at.isoformat() if bsd_state.updated_at else None
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation and all associated data"""
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()

    if not conv:
        raise HTTPException(status_code=403, detail="Conversation not found or unauthorized")

    # Remove all related data to avoid FK constraint issues
    db.query(ConversationFlag).filter(ConversationFlag.conversation_id == conversation_id).delete()
    db.query(BsdAuditLog).filter(BsdAuditLog.conversation_id == conversation_id).delete()
    db.query(BsdSessionState).filter(BsdSessionState.conversation_id == conversation_id).delete()

    db.delete(conv)
    db.commit()
    return {"status": "deleted"}

@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
    message: MessageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Send message with auto-title generation on first message"""
    
    # Get conversation and verify ownership
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    
    if not conv:
        raise HTTPException(status_code=403, detail="Conversation not found or unauthorized")
    
    # Save user message
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=message.content
    )
    db.add(user_msg)
    db.commit()
    
    # Check if this is the FOURTH user message and generate title
    # (We wait for more context to generate a more accurate title)
    user_message_count = db.query(Message)\
        .filter(Message.conversation_id == conversation_id, Message.role == "user")\
        .count()
    
    if user_message_count == 4 and conv.title == "New Conversation":  # Fourth user message (enough context)
        # Get all user messages for better context
        user_messages = db.query(Message)\
            .filter(Message.conversation_id == conversation_id, Message.role == "user")\
            .order_by(Message.timestamp)\
            .all()
        
        # Combine user messages for title generation (with context)
        context = " | ".join([msg.content[:100] for msg in user_messages if msg.content])
        
        if context:
            # Generate smart title using OpenAI with more context
            conv.title = generate_smart_title(context, message.language or "he")
            db.commit()
            print(f"✨ Auto-generated title: {conv.title}")
    
    # Cache values BEFORE async operations (avoid DetachedInstanceError)
    current_phase_cache = conv.current_phase
    user_msg_timestamp = str(user_msg.timestamp)
    user_display_name_cache = user.display_name  # Cache user profile data
    user_gender_cache = user.gender
    # Cache last 10 messages for quality check (must happen before async generator)
    history_cache = [
        {"role": msg.role, "content": msg.content}
        for msg in conv.messages[-10:]
    ]
    
    # Stream response
    async def response_generator():
        nonlocal current_phase_cache  # Access the outer variable
        full_response = ""
        bsd_metadata: Dict = {}
        
        try:
            # Auto-detect language from message content (more reliable than frontend i18n)
            def detect_language(text: str) -> str:
                """Detect if message is Hebrew or English based on character content"""
                import re
                hebrew_chars = re.findall(r'[\u0590-\u05FF]', text)
                english_chars = re.findall(r'[a-zA-Z]', text)
                
                # If more Hebrew than English, it's Hebrew
                if len(hebrew_chars) > len(english_chars):
                    return "he"
                # If more English than Hebrew, it's English
                elif len(english_chars) > len(hebrew_chars):
                    return "en"
                # Default to Hebrew (most common)
                else:
                    return message.language or "he"
            
            detected_language = detect_language(message.content)
            
            coach_text, bsd_metadata = await bsd_engine.run_turn(
                db=db,
                conversation_id=conversation_id,
                user_message=message.content,
                language=detected_language,
                user_name=user_display_name_cache,
                user_gender=user_gender_cache,
            )

            # Update display phase (NOT the source of truth; BSD state is in bsd_session_states)
            old_phase = current_phase_cache
            new_phase = bsd_metadata.get("bsd_stage") or current_phase_cache
            conv.current_phase = new_phase
            current_phase_cache = new_phase  # Update cache
            
            if old_phase != new_phase:
                if not conv.phase_history:
                    conv.phase_history = []
                conv.phase_history.append(
                    {"from": old_phase, "to": new_phase, "timestamp": user_msg_timestamp}
                )
                db.commit()

            # Stream in small chunks to keep the existing frontend streaming UX
            chunk_size = 80
            for i in range(0, len(coach_text), chunk_size):
                chunk = coach_text[i : i + chunk_size]
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            # Save assistant message with BSD metadata
            assistant_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
                meta={
                    "bsd": bsd_metadata,
                    "phase_at_response": current_phase_cache,
                }
            )
            db.add(assistant_msg)
            db.commit()
            
            # Send completion with phase info
            final_metadata = {
                'done': True, 
                'message_id': assistant_msg.id,
                'current_phase': current_phase_cache,
                'phase_changed': bool(bsd_metadata.get("phase_changed", False)),
            }
            
            # Optional: pass tool_call through if/when BSD core emits it
            if bsd_metadata and "tool_call" in bsd_metadata:
                final_metadata["tool_call"] = bsd_metadata["tool_call"]
            
            yield f"data: {json.dumps(final_metadata)}\n\n"
            
            # Trigger async quality check (zero latency impact on user)
            background_tasks.add_task(
                run_quality_check,
                conversation_id=conversation_id,
                message_id=assistant_msg.id,
                history=history_cache,
                current_stage=current_phase_cache,
                latest_response=full_response,
                db_session=db
            )
            
        except Exception as e:
            # Handle any unexpected errors during streaming
            print(f"❌ ERROR in response_generator: {e}")
            import traceback
            traceback.print_exc()
            
            # Send error message to frontend
            error_msg = "מצטער, היתה שגיאה. אנא נסה שוב." if (message.language or "he") == "he" else "Sorry, there was an error. Please try again."
            yield f"data: {json.dumps({'content': error_msg})}\n\n"
            
            # CRITICAL: Send done signal even on error so loading dots disappear
            done_data = {
                "done": True, 
                "error": True,
                "current_phase": current_phase_cache
            }
            yield f"data: {json.dumps(done_data)}\n\n"
    
    return StreamingResponse(response_generator(), media_type="text/event-stream")

