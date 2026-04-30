"""
When to attach interactive InsightHub tools to a V2 chat response.

S11 (profit_loss): still on first entry into the stage (matches methodology: table right after stance).

S12 (trait_picker): only when the model sets collected_data.offer_trait_picker explicitly
(after explanation + verbal recap in coach_message — see stage prompts). No saturation fallback:
surfacing the form without the flag caused tables to appear without proper framing.
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
        "instruction_he": (
            "כרטיס הכמ״ז מחלק תכונות לשני צדדים לפי השיטה: "
            "**מקור** — אור, ערכים ושליחות (נפש אלוקית); **טבע** — צרכים, הגנות ודחפים שמושכים למטה (ניהול בשכל, לא «אויב»). "
            "הוסף עד 6 פריטים בכל צד; הראשון בכל עמודה הוא התכונה המובילה. שלח כשסיימת — המאמן ימשיך אחרי זה."
        ),
        "instruction_en": (
            "The KaMaZ card splits traits into two sides: **Source** — light, values, mission (divine soul); "
            "**Nature** — needs, defenses, downward pulls (working material to steer with intellect, not an 'enemy'). "
            "Add up to 6 items per side; the first in each column is the leading trait. Submit when done — the coach continues after that."
        ),
    },
}

def _trait_picker_eligible(state: Dict[str, Any]) -> bool:
    if state.get("trait_picker_tool_sent"):
        return False
    cd = state.get("collected_data") or {}
    return bool(cd.get("offer_trait_picker"))


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
