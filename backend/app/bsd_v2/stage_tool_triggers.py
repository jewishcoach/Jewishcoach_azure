"""
When to attach interactive InsightHub tools to a V2 chat response.

S11 (profit_loss): still on first entry into the stage (matches booklet: table right after stance).

S12 (trait_picker): deferred per booklet order — after explanation / verbal consolidation;
the model sets collected_data.offer_trait_picker, with a saturation fallback if it forgets.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

STAGE_TOOL_TRIGGERS: Dict[str, Dict[str, Any]] = {
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
        "title_he": 'כוחות מקור וטבע (כמ"ז)',
        "title_en": "Source & Nature Forces (KMZ)",
        "instruction_he": "מהם הערכים והאמונות שמניעים אותך (מקור)? ומהן היכולות והכישרונות הטבעיים שלך (טבע)?",
        "instruction_en": "What are the values and beliefs that drive you (source)? And what are your natural abilities and talents (nature)?",
    },
}

# If the model never sets offer_trait_picker, still surface the form once engagement in S12 is high enough.
_TRAIT_PICKER_SATURATION_FALLBACK = 0.82


def _trait_picker_eligible(state: Dict[str, Any]) -> bool:
    if state.get("trait_picker_tool_sent"):
        return False
    cd = state.get("collected_data") or {}
    if cd.get("offer_trait_picker"):
        return True
    sat = float(state.get("saturation_score") or 0)
    return sat >= _TRAIT_PICKER_SATURATION_FALLBACK


def resolve_post_turn_tool_call(prev_step: str, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Decide whether this response should include a tool_call for the client.

    prev_step: current_step before the coach turn (from API snapshot).
    state: full V2 state after handle_conversation (includes merged collected_data).
    """
    new_step = state.get("current_step", "S0")

    if new_step == prev_step:
        if new_step == "S12" and _trait_picker_eligible(state):
            return STAGE_TOOL_TRIGGERS["S12"]
        return None

    if new_step == "S11":
        return STAGE_TOOL_TRIGGERS["S11"]

    if new_step == "S12" and _trait_picker_eligible(state):
        return STAGE_TOOL_TRIGGERS["S12"]

    return None


def mark_trait_picker_sent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Mutate and return state so we do not re-offer the trait picker in the same conversation."""
    state["trait_picker_tool_sent"] = True
    return state
