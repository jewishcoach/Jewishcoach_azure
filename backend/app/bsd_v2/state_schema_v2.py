"""
BSD V2 State Schema - Simplified, flexible state management.

Unlike V1's rigid Pydantic models, V2 uses simple dicts for flexibility.
The LLM manages its own state through JSON responses.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


def create_initial_state(
    conversation_id: str,
    user_id: str,
    language: str = "he"
) -> Dict[str, Any]:
    """
    Create initial conversation state for V2.
    
    Returns:
        Simple dict with conversation metadata
    """
    return {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "language": language,
        "created_at": datetime.utcnow().isoformat(),
        
        # LLM-managed state (extracted from responses)
        "current_step": "S0",  # S0-S12
        "collected_data": {
            "topic": None,
            "event_description": None,
            # S3: Emotions (actual)
            "emotions": [],
            # S4: Thought (actual)
            "thought": None,
            # S5: Action (actual + desired)
            "action_actual": None,
            "action_desired": None,
            # S5: Emotion & Thought (desired - optional)
            "emotion_desired": None,  # ✨ NEW: איך רצה להרגיש
            "thought_desired": None,  # ✨ NEW: מה רצה לחשוב
            # S6: Gap
            "gap_name": None,
            "gap_score": None,
            # S7: Pattern
            "pattern": None,  # דפוס חוזר
            # S8: Stance (gains + losses)
            "stance": {
                "gains": [],  # מה מרוויח
                "losses": []  # מה מפסיד
            },
            # S9: Forces
            "forces": {
                "source": [],  # מקור - ערכים
                "nature": []  # טבע - יכולות
            },
            # S10: Renewal
            "renewal": None,  # בחירה/עמדה חדשה
            # S11: Vision
            "vision": None,
            # S12: Commitment
            "commitment": None,  # מחויבות קונקרטית
        },
        
        # Conversation history (for context)
        "messages": [],
        
        # V2-specific metadata
        "saturation_score": 0.0,  # How deeply user engaged in current step
        "gate_status": {},  # Track which gates passed (e.g., {"S3_emotions": 4})
        "reflection_notes": [],  # Internal coach observations
    }


def add_message(
    state: Dict[str, Any],
    sender: str,  # "user" or "coach"
    content: str,
    internal_state: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Add message to conversation history.
    
    Args:
        state: Current state
        sender: "user" or "coach"
        content: Message content
        internal_state: LLM's internal state (extracted from JSON response)
    
    Returns:
        Updated state
    """
    state["messages"].append({
        "sender": sender,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
        "internal_state": internal_state  # Only for coach messages
    })
    
    # Update top-level state from internal_state
    if internal_state and sender == "coach":
        state["current_step"] = internal_state.get("current_step", state["current_step"])
        
        # Merge collected_data (don't overwrite topic with empty - preserve from S1)
        if "collected_data" in internal_state:
            for key, value in internal_state["collected_data"].items():
                if value is None:
                    continue
                if key == "topic":
                    v = str(value).strip() if value else ""
                    if not v or v in ("[נושא]", "[topic]"):
                        continue  # don't overwrite topic with empty/placeholder
                state["collected_data"][key] = value
        
        # Update saturation score
        if "saturation_score" in internal_state:
            state["saturation_score"] = internal_state["saturation_score"]
    
    return state


def get_conversation_history(state: Dict[str, Any], last_n: int = 10) -> List[Dict[str, Any]]:
    """
    Get last N messages for context building.
    
    Args:
        state: Current state
        last_n: Number of recent messages to return
    
    Returns:
        List of message dicts
    """
    return state["messages"][-last_n:] if state["messages"] else []
