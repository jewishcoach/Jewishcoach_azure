"""
When to attach interactive InsightHub tools to a V2 chat response.

S11 (profit_loss): still on first entry into the stage (matches methodology: table right after stance).

S12 (trait_picker): only when the model sets collected_data.offer_trait_picker explicitly
(after explanation + verbal recap in coach_message — see stage prompts). No saturation fallback:
surfacing the form without the flag caused tables to appear without proper framing.

V3 (ux_version=3): Extended tool triggers for hybrid chat+UI flow.
Each stage transition can emit a structured UI tool_call with pre-populated data.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

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

# ---------------------------------------------------------------------------
# V3 Tool Definitions — structured UI components for hybrid chat+UI flow
# ---------------------------------------------------------------------------

V3_TOOL_DEFS: Dict[str, Dict[str, Any]] = {
    "event_form": {
        "type": "tool",
        "tool_type": "event_form",
        "title_he": "ספר על האירוע",
        "instruction_he": "תאר אירוע ספציפי שקרה לאחרונה — מתי, עם מי, ומה קרה בקצרה.",
    },
    "emotion_selector": {
        "type": "tool",
        "tool_type": "emotion_selector",
        "title_he": "מה הרגשת באותו רגע?",
        "instruction_he": "בחר לפחות 2 רגשות שהרגשת באותו אירוע.",
    },
    "action_field": {
        "type": "tool",
        "tool_type": "action_field",
        "title_he": "מה עשית בפועל?",
        "instruction_he": "תאר את הפעולה שעשית — משהו שאפשר לראות מבחוץ.",
    },
    "matzui_summary": {
        "type": "tool",
        "tool_type": "matzui_summary",
        "title_he": "סיכום המצוי",
        "instruction_he": "בדוק שהתמונה מדויקת — הרגש, המחשבה והפעולה באותו רגע.",
    },
    "comparison_card": {
        "type": "tool",
        "tool_type": "comparison_card",
        "title_he": "מצוי מול רצוי",
        "instruction_he": "באותו רגע בדיוק — מה היית רוצה להרגיש, לחשוב ולעשות?",
    },
    "gap_card": {
        "type": "tool",
        "tool_type": "gap_card",
        "title_he": "הפער",
        "instruction_he": "תן שם לפער, דרג את העוצמה, ובדוק אם יש כאן הזדמנות.",
    },
    "sentence_builder": {
        "type": "tool",
        "tool_type": "sentence_builder",
        "title_he": "החוק הפנימי שלי",
        "instruction_he": "השלם: 'ככה זה אצלי — כי...' ומה האמונה שמאחורי זה.",
    },
    "balance_scale": {
        "type": "tool",
        "tool_type": "balance_scale",
        "title_he": "מאזן רווח והפסד",
        "instruction_he": "מה אתה מרוויח מלהחזיק בדפוס הזה? ומה אתה מפסיד?",
    },
    "trait_card_builder": {
        "type": "tool",
        "tool_type": "trait_card_builder",
        "title_he": "כרטיס מהות זהות",
        "instruction_he": (
            "בנה את כרטיס הכוחות שלך — 6 תכונות מקור ו-6 תכונות טבע. "
            "בחר מההצעות או כתוב משלך. גרור לסדר — הראשון הוא המוביל."
        ),
    },
    "declaration_card": {
        "type": "tool",
        "tool_type": "declaration_card",
        "title_he": "ההכרזה החדשה",
        "instruction_he": "מה האמונה החדשה שמחליפה את הישנה? ומה תעשה אחרת?",
    },
    "commitment_card": {
        "type": "tool",
        "tool_type": "commitment_card",
        "title_he": "המחויבות שלי",
        "instruction_he": "מה אתה מתחייב לעשות, מתי, ואיפה או מול מי?",
    },
}


def _trait_picker_eligible(state: Dict[str, Any]) -> bool:
    if state.get("trait_picker_tool_sent"):
        return False
    cd = state.get("collected_data") or {}
    return bool(cd.get("offer_trait_picker"))


def _build_v3_tool_call(tool_key: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Build a V3 tool_call with pre-populated data from collected_data."""
    base = dict(V3_TOOL_DEFS[tool_key])
    cd = state.get("collected_data") or {}

    if tool_key == "emotion_selector":
        base["data"] = {
            "suggested_emotions": _suggest_emotions_for_event(cd),
            "event_summary": cd.get("event_description", ""),
        }
    elif tool_key == "comparison_card":
        base["data"] = {
            "emotions": cd.get("emotions", []),
            "thought": cd.get("thought", ""),
            "action_actual": cd.get("action_actual", ""),
        }
    elif tool_key == "matzui_summary":
        base["data"] = {
            "emotions": cd.get("emotions", []),
            "thought": cd.get("thought", ""),
            "action_actual": cd.get("action_actual", ""),
        }
    elif tool_key == "sentence_builder":
        base["data"] = {
            "pattern": cd.get("pattern", ""),
        }
    elif tool_key == "trait_card_builder":
        base["data"] = {
            "suggestions": _generate_trait_suggestions(cd),
        }
    elif tool_key == "declaration_card":
        base["data"] = {
            "old_pattern": cd.get("pattern", ""),
            "old_paradigm": cd.get("paradigm", ""),
        }

    return base


def _suggest_emotions_for_event(cd: Dict[str, Any]) -> List[str]:
    """Suggest relevant emotions based on the event description."""
    event = (cd.get("event_description") or "").lower()

    # Conflict/argument keywords
    conflict_emotions = ["כעס", "תסכול", "עלבון", "אכזבה", "חוסר אונים"]
    rejection_emotions = ["עלבון", "בושה", "בדידות", "עצב", "פחד"]
    loss_emotions = ["עצב", "אבל", "ריקנות", "בדידות", "חרדה"]
    pressure_emotions = ["חרדה", "לחץ", "תסכול", "חוסר אונים", "פחד"]
    betrayal_emotions = ["עלבון", "כעס", "אכזבה", "בושה", "אשמה"]

    conflict_words = ["מריבה", "ריב", "ויכוח", "צעקות", "צעק", "כעס", "התנגש"]
    rejection_words = ["דחה", "דחייה", "התעלם", "לא ראה", "לא שמע", "ביטל"]
    loss_words = ["עזב", "נפרד", "איבד", "מת", "הלך", "נגמר"]
    pressure_words = ["לחץ", "דרש", "ציפ", "מועד", "מבחן", "החליט בשבילי"]
    betrayal_words = ["שיקר", "בגד", "הפר", "לא קיים", "אמר ולא"]

    suggested = []
    if any(w in event for w in conflict_words):
        suggested.extend(conflict_emotions)
    if any(w in event for w in rejection_words):
        suggested.extend(rejection_emotions)
    if any(w in event for w in loss_words):
        suggested.extend(loss_emotions)
    if any(w in event for w in pressure_words):
        suggested.extend(pressure_emotions)
    if any(w in event for w in betrayal_words):
        suggested.extend(betrayal_emotions)

    # Deduplicate while preserving order, limit to 6
    seen = set()
    result = []
    for e in suggested:
        if e not in seen:
            seen.add(e)
            result.append(e)
    return result[:6] if result else ["כעס", "עצב", "תסכול", "חרדה", "עלבון", "אכזבה"]


def _generate_trait_suggestions(cd: Dict[str, Any]) -> Dict[str, List[str]]:
    """Generate trait suggestions for TraitCardBuilder from collected_data."""
    source_hints: List[str] = []
    nature_hints: List[str] = []

    # Derive source hints from positive/desired elements
    if cd.get("emotion_desired"):
        source_hints.append(cd["emotion_desired"])
    if cd.get("thought_desired"):
        source_hints.append(cd["thought_desired"])

    # Derive nature hints from pattern/negative elements
    if cd.get("pattern"):
        nature_hints.append(cd["pattern"])
    emotions = cd.get("emotions") or []
    nature_hints.extend(emotions[:3])

    stance = cd.get("stance") or {}
    for gain in (stance.get("gains") or [])[:2]:
        nature_hints.append(gain)
    for loss in (stance.get("losses") or [])[:2]:
        source_hints.append(loss)

    return {"source": source_hints[:6], "nature": nature_hints[:6]}


def _resolve_v3_tool_call(prev_step: str, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """V3-specific tool resolution with broader stage triggers."""
    new_step = state.get("current_step", "S0")
    cd = state.get("collected_data") or {}

    # S12 with offer_trait_picker → trait_card_builder (V3 version)
    if new_step == "S12" and _trait_picker_eligible(state):
        return _build_v3_tool_call("trait_card_builder", state)

    # Only trigger on step transitions (new_step != prev_step)
    if new_step == prev_step:
        # Special case: S5 with action_actual already filled → matzui_summary
        if new_step == "S5" and cd.get("action_actual") and not state.get("_matzui_summary_sent"):
            return _build_v3_tool_call("matzui_summary", state)
        return None

    step_tool_map: Dict[str, str] = {
        "S2": "event_form",
        "S3": "emotion_selector",
        "S5": "action_field",
        "S6": "comparison_card",
        "S7": "gap_card",
        "S9": "sentence_builder",
        "S11": "balance_scale",
        "S13": "declaration_card",
        "S15": "commitment_card",
    }

    tool_key = step_tool_map.get(new_step)
    if tool_key:
        return _build_v3_tool_call(tool_key, state)

    return None


def resolve_post_turn_tool_call(
    prev_step: str,
    state: Dict[str, Any],
    ux_version: int = 2,
) -> Optional[Dict[str, Any]]:
    """
    Decide whether this response should include a tool_call for the client.

    prev_step: current_step before the coach turn (from API snapshot).
    state: full V2 state after handle_conversation (includes merged collected_data).
    ux_version: UX version from X-UX-Version header (2 or 3).
    """
    if ux_version >= 3:
        return _resolve_v3_tool_call(prev_step, state)

    # V2 behavior (unchanged)
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


def mark_matzui_summary_sent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Mutate and return state so we do not re-offer matzui_summary."""
    state["_matzui_summary_sent"] = True
    return state
