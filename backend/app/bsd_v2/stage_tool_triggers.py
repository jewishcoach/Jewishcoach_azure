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
            "**מקור** — אור, ערכים ושליחות (נפש אלוקית); **טבע** — תכונות ונטיות טבעיות, הכלים שאיתם אתה פועל (ניהול בשכל, לא «אויב»). "
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
        "instruction_he": (
            "הדפוס הוא מה שאתה **עושה**. הפרדיגמה היא ה'חוק' שגורם לך להאמין שזו הדרך הנכונה. "
            "השלם: 'ככה זה אצלי — ...' — החוק שאומר לך איך נכון להגיב (לא הפעולה עצמה, ולא רק החשש ממה שיקרה)."
        ),
    },
    "balance_scale": {
        "type": "tool",
        "tool_type": "balance_scale",
        "title_he": "מאזן רווח והפסד",
        "instruction_he": "מה אתה מרוויח מלהחזיק בעמדה הזו? ומה אתה מפסיד?",
    },
    "kamaz_discovery": {
        "type": "tool",
        "tool_type": "kamaz_discovery",
        "title_he": "הבזקי מקור וטבע",
        "instruction_he": "השלם כל משפט במילים שלך — קצר, מה שעולה ראשון.",
    },
    "trait_card_builder": {
        "type": "tool",
        "tool_type": "trait_card_builder",
        "title_he": "כרטיס מהות זהות",
        "instruction_he": (
            "בחר 6 תכונות מקור ו-6 תכונות טבע — מתוך מה שעלה בתשובות שלך, מהמאגר, או במילים שלך."
        ),
    },
    "declaration_card": {
        "type": "tool",
        "tool_type": "declaration_card",
        "title_he": "ההכרזה החדשה",
        "instruction_he": "מהי העמדה החדשה שאתה בוחר — 'אני מאמין ש…'? ומה תעשה אחרת?",
    },
    "commitment_card": {
        "type": "tool",
        "tool_type": "commitment_card",
        "title_he": "הבקשה שלי לאימון",
        "instruction_he": "בקשה לאימון במבנה החוברת: על איזו קומה תתאמן, מתוך אילו כוחות שלך, ואיזו תוצאה מדידה תשיג.",
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
    elif tool_key == "kamaz_discovery":
        from .kamaz_bank import questions_for
        base["data"] = {"questions": questions_for(state.get("_user_gender"))}
    elif tool_key == "trait_card_builder":
        from .kamaz_bank import bank_for_card
        found = cd.get("kamaz_suggestions") if isinstance(cd.get("kamaz_suggestions"), dict) else {}
        base["data"] = {
            "bank": bank_for_card(),
            # "עלה מתוך מה שכתבת" — each with the words it came from (empty when he declined the 3+3)
            "suggested": found.get("suggested") or {"source": [], "nature": []},
            # the gentle default for the forces for this event (step 4)
            "event_rank": found.get("event_rank") or {"source": [], "nature": []},
            "suggestions": _generate_trait_suggestions(cd),  # the previous card version (cached clients)
        }
    elif tool_key == "declaration_card":
        stance = cd.get("stance") or {}
        stance = stance if isinstance(stance, dict) else {}
        # The new stance faces the old one, at the same floor (booklet p.29-30; expert: the stance IS the belief —
        # one level, "אני מאמין ש...")
        base["data"] = {
            "old_pattern": cd.get("pattern", ""),
            "old_paradigm": cd.get("paradigm", ""),
            "old_stance": stance.get("short") or stance.get("reality_belief", ""),
        }
    elif tool_key == "commitment_card":
        # בקשה לאימון (booklet p.37-38): prefill the client's own old/new floors and his כמ"ז
        forces = cd.get("forces") or {}
        stance = cd.get("stance") or {}
        base["data"] = {
            "forces_source": list(forces.get("source") or [])[:6] if isinstance(forces, dict) else [],
            "forces_nature": list(forces.get("nature") or [])[:6] if isinstance(forces, dict) else [],
            # the forces he chose for this event at S12 (spec: selected_makor / selected_teva) — preselected on the card
            "selected_source": list(cd.get("selected_makor") or []),
            "selected_nature": list(cd.get("selected_teva") or []),
            "old": {
                "pattern": cd.get("pattern", ""),
                "paradigm": cd.get("paradigm", ""),
                # the stance = his perception sentence, distilled (≤12 words) so it reads inside the booklet template
                "stance": (stance.get("short") or stance.get("reality_belief", "")) if isinstance(stance, dict) else "",
            },
            "new": {"stance": cd.get("renewal_belief", ""), "pattern": cd.get("new_action", "")},
        }

    # every card is worded in the client's gender ("בחרי", "את מאמינה") — the coach already is
    base["data"] = {**(base.get("data") or {}), "gender": state.get("_user_gender")}
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


# BSD: source = values (נפש אלוקית), nature = natural tendencies and needs in their healthy form (נפש טבעית) — traits
# of life as a whole, not of the coaching event. The bank is kamaz_bank (the S12 spec); fears and avoidances are not
# nature forces (expert review) — a request "אפעל מתוך הטבע שלי, שהוא פחד מדחייה" is absurd.
from .kamaz_bank import NATURE_TRAITS as _NATURE_BANK, SOURCE_TRAITS as _SOURCE_BANK  # noqa: E402

_SOURCE_TRAITS = [t["short"] for t in _SOURCE_BANK]
_NATURE_TRAITS = [t["short"] for t in _NATURE_BANK]
# Pattern/belief words → the natural qualities and values most likely in play, listed first
_NATURE_HINTS = [
    (("שותק", "שתקתי", "נסגר", "בולע", "לא אומר", "לא אמרתי", "מחייך", "בלגן", "עניין"),
     ["שאיפה להרמוניה ושקט", "רגישות לתגובות הסביבה"]),
    (("צועק", "צעקתי", "מתפרץ", "כעס", "בכוח", "שולט"), ["צורך בשליטה וודאות", "שמירה על גבולות וצדק"]),
    (("לא רואים", "שקוף", "לא סופרים", "לא חשוב", "לא נספר"), ["צורך בהערכה וכבוד", "צורך בשייכות וקבלה"]),
    (("נכשל", "כישלון", "לא מספיק", "גרוע"), ["יסודיות ודיוק", "שאיפה למצוינות"]),
]
_SOURCE_HINTS = [
    (("להגיד", "לומר", "קול", "לבטא", "ישיר"), ["אומץ", "כנות"]),
    (("קרבה", "קשר", "ביחד", "חיבוק"), ["אהבה", "נתינה"]),
    (("רגוע", "סבלנות", "להקשיב"), ["הכלה", "חמלה"]),
    (("אחריות", "לעמוד", "גבול"), ["אחריות", "יושרה"]),
]


def _ordered(defaults: List[str], hints, text: str) -> List[str]:
    picked: List[str] = []
    for words, traits in hints:
        if any(w in text for w in words):
            picked.extend(t for t in traits if t not in picked)
    return picked + [t for t in defaults if t not in picked]


def _generate_trait_suggestions(cd: Dict[str, Any]) -> Dict[str, List[str]]:
    """Trait suggestions for TraitCardBuilder: BSD values (source) and needs (nature),
    ordered by what the user's pattern / belief / desired state point to."""
    stance = cd.get("stance") or {}
    pattern_text = " ".join(str(v or "") for v in (
        cd.get("pattern"), cd.get("paradigm"), stance.get("reality_belief"), cd.get("thought"),
    ))
    desired_text = " ".join(str(v or "") for v in (
        cd.get("action_desired"), cd.get("thought_desired"), cd.get("emotion_desired"),
    ))
    return {
        "source": _ordered(_SOURCE_TRAITS, _SOURCE_HINTS, desired_text)[:12],
        "nature": _ordered(_NATURE_TRAITS, _NATURE_HINTS, pattern_text)[:12],
    }


_INTERPRETIVE_ONLY = {
    "ויתרתי", "נסגרתי", "נאטמתי", "ברחתי", "כלום",
    "שום דבר", "נשברתי", "התפרקתי", "התרסקתי", "נפלתי",
    "קרסתי", "לא עשיתי כלום", "הרגשתי חלש", "הרגשתי רע",
}


def _action_looks_interpretive(action: str) -> bool:
    """Heuristic: short vague actions that need grounding before summary.
    A long description with multiple concrete details is likely observable."""
    action = action.strip()
    if not action:
        return True
    if len(action) < 12:
        return True
    # Long descriptions with commas/conjunctions are likely multi-part observable actions
    if len(action) > 30 and ("," in action or " ו" in action):
        return False
    return action in _INTERPRETIVE_ONLY


def _s12_tool_call(prev_step: str, state: Dict[str, Any], from_tool_submission: Optional[str]) -> Optional[Dict[str, Any]]:
    cd = state.get("collected_data") or {}
    if state.get("trait_picker_tool_sent") or prev_step == "__stage_intro__":
        return None
    if from_tool_submission == "kamaz_discovery" or cd.get("kamaz_answers"):
        return _build_v3_tool_call("trait_card_builder", state)
    permission = state.get("kamaz_permission")
    if permission == "no":
        return _build_v3_tool_call("trait_card_builder", state)
    if permission == "yes" and not state.get("kamaz_discovery_sent"):
        return _build_v3_tool_call("kamaz_discovery", state)
    return None  # waiting for the answer to the permission question


def _resolve_v3_tool_call(prev_step: str, state: Dict[str, Any], from_tool_submission: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """V3-specific tool resolution with broader stage triggers."""
    new_step = state.get("current_step", "S0")
    cd = state.get("collected_data") or {}

    # S12 (spec "כמ"ז בתוך אימון 3+3"): the opening turn asks permission (no card); "כן" → the 3+3 discovery card;
    # "לא" or after the 3+3 → the 6+6 card (with the event choice); after it — no card, the stage closes.
    if new_step == "S12":
        return _s12_tool_call(prev_step, state, from_tool_submission)

    # Only trigger on step transitions (new_step != prev_step)
    if new_step == prev_step:
        # Special case: S5 with action_actual already filled → matzui_summary
        # On action_field submission: only show if the action looks observable.
        # Interpretive actions (short, no verb of motion/speech) get delayed
        # so the coach can ask a grounding question first.
        if new_step == "S5" and cd.get("action_actual") and not state.get("_matzui_summary_sent"):
            if from_tool_submission == "action_field":
                action = cd.get("action_actual", "")
                if _action_looks_interpretive(action):
                    return None
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


# Resume: cards live in the client, not in the saved history — a fresh window showed only the coach's lead-in
# ("עכשיו נבדוק יחד מה הפער…") with nothing to answer (pilot couple, Oct 30). The step's card comes back while its
# data is still missing and the coach's last message is a statement; a question there is answered in the chat.
_RESUME_CARDS = {
    "S2": ("event_form", "event_description"),
    "S3": ("emotion_selector", "emotions"),
    "S5": ("action_field", "action_actual"),
    "S6": ("comparison_card", "action_desired"),
    "S7": ("gap_card", "gap_name"),
    "S9": ("sentence_builder", "paradigm"),
    "S11": ("balance_scale", "stance.gains"),
    "S13": ("declaration_card", "renewal_belief"),
    "S15": ("commitment_card", "commitment"),
}


def pending_card_on_resume(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if int(state.get("ux_version", 2) or 2) < 3:
        return None
    from .safety_check import is_safety_message
    from .partner_safety import is_partner_safety_message
    last_coach = next((m.get("content") or "" for m in reversed(state.get("messages") or [])
                       if m.get("sender") == "coach"), "")
    if not last_coach or is_safety_message(last_coach) or is_partner_safety_message(last_coach):
        return None
    step = state.get("current_step")
    cd = state.get("collected_data") or {}
    asks = last_coach.rstrip().endswith("?")
    if step == "S5" and cd.get("action_actual"):
        return None if asks else _build_v3_tool_call("matzui_summary", state)
    entry = _RESUME_CARDS.get(step)
    if not entry or (asks and step != "S2"):  # S2: the event card is the only way into the process
        return None
    tool, key = entry
    filled = (cd.get("stance") or {}).get("gains") if key == "stance.gains" else cd.get(key)
    return None if filled else _build_v3_tool_call(tool, state)


def resolve_post_turn_tool_call(
    prev_step: str,
    state: Dict[str, Any],
    ux_version: int = 2,
    from_tool_submission: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Decide whether this response should include a tool_call for the client.

    prev_step: current_step before the coach turn (from API snapshot).
    state: full V2 state after handle_conversation (includes merged collected_data).
    ux_version: UX version from X-UX-Version header (2 or 3).
    from_tool_submission: tool_type if this call originated from a tool submit endpoint.
    """
    if ux_version >= 3:
        return _resolve_v3_tool_call(prev_step, state, from_tool_submission=from_tool_submission)

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


def mark_kamaz_discovery_sent(state: Dict[str, Any]) -> Dict[str, Any]:
    state["kamaz_discovery_sent"] = True
    return state


def mark_matzui_summary_sent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Mutate and return state so we do not re-offer matzui_summary."""
    state["_matzui_summary_sent"] = True
    return state
