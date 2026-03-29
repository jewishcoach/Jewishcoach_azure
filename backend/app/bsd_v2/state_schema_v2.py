"""
BSD V2 State Schema - Simplified, flexible state management.

Unlike V1's rigid Pydantic models, V2 uses simple dicts for flexibility.
The LLM manages its own state through JSON responses.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


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
        "created_at": datetime.now(timezone.utc).isoformat(),
        
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
            "gap_booklet_moves": [],  # S7: belief | opportunity | dwelling | waiver | authenticity
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
            # Context entities (updated throughout the whole conversation)
            "entities": {
                "people": [],       # שמות ותפקידי אנשים
                "places": [],       # מקומות ספציפיים
                "key_examples": []  # דוגמאות ספציפיות בלשון המתאמן
            },
        },
        
        # Conversation history (for context)
        "messages": [],
        
        # V2-specific metadata
        "saturation_score": 0.0,  # How deeply user engaged in current step
        "stage_saturation": {},   # Peak saturation recorded per stage: {"S1": 0.9, "S2": 0.85, ...}
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "internal_state": internal_state  # Only for coach messages
    })
    
    # Update top-level state from internal_state
    if internal_state and sender == "coach":
        # Track peak saturation per stage BEFORE advancing (the score belongs to the stage we were in)
        old_step = state.get("current_step", "S0")
        new_score = internal_state.get("saturation_score")
        if isinstance(new_score, (int, float)):
            stage_sat = state.setdefault("stage_saturation", {})
            stage_sat[old_step] = max(stage_sat.get(old_step, 0.0), float(new_score))

        new_step = internal_state.get("current_step", state["current_step"])
        state["current_step"] = new_step

        # Capture S2 anchor when transitioning away from S2 for the first time.
        # The anchor preserves raw user messages (names, places, specific wording)
        # that would otherwise be truncated from the rolling history window.
        if old_step == "S2" and new_step not in ("S0", "S1", "S2") and "s2_anchor" not in state:
            s2_user_msgs = [
                m["content"] for m in state["messages"]
                if m["sender"] == "user" and m["content"]
            ]
            # Keep last 3 user messages from S2 context (most relevant event descriptions)
            state["s2_anchor"] = s2_user_msgs[-3:] if s2_user_msgs else []

        # Merge collected_data (don't overwrite existing values with empty/null)
        if "collected_data" in internal_state:
            for key, value in internal_state["collected_data"].items():
                # Skip None and empty containers (model_dump returns [] for unused List fields)
                if value is None or value == [] or value == {}:
                    continue
                if key == "topic":
                    v = str(value).strip() if value else ""
                    if not v or v in ("[נושא]", "[topic]"):
                        continue  # don't overwrite topic with empty/placeholder
                # gap_booklet_moves: union-merge tokens (belief, opportunity, …)
                if key == "gap_booklet_moves" and isinstance(value, list):
                    existing_moves = state["collected_data"].setdefault("gap_booklet_moves", [])
                    seen_moves = set(existing_moves)
                    for item in value:
                        if item and item not in seen_moves:
                            existing_moves.append(item)
                            seen_moves.add(item)
                    continue
                if key == "entities" and isinstance(value, dict):
                    existing_entities = state["collected_data"].setdefault("entities", {
                        "people": [], "places": [], "key_examples": []
                    })
                    for sub_k in ("people", "places", "key_examples"):
                        new_items = value.get(sub_k) or []
                        if new_items:
                            seen = set(existing_entities.get(sub_k, []))
                            for item in new_items:
                                if item and item not in seen:
                                    existing_entities.setdefault(sub_k, []).append(item)
                                    seen.add(item)
                    continue
                # For other nested dicts (stance, forces): merge instead of overwrite
                if isinstance(value, dict) and isinstance(state["collected_data"].get(key), dict):
                    existing = state["collected_data"][key]
                    for sub_k, sub_v in value.items():
                        if sub_v is not None and sub_v != []:
                            existing[sub_k] = sub_v
                else:
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
