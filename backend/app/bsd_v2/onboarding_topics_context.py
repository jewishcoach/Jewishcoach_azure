"""Inject optional coach hint from onboarding topic selections (user.preferences)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

TOPIC_IDS = frozenset(
    {
        "goals",
        "parenting",
        "relationships",
        "career",
        "wellbeing",
        "personal_growth",
    }
)

# Align with frontend `bsdOnboarding.topic.*` copy (short labels for prompt).
LABEL_HE: Dict[str, str] = {
    "goals": "השגת יעדים",
    "parenting": "הורות",
    "relationships": "זוגיות ומערכות יחסים",
    "career": "קריירה ועבודה",
    "wellbeing": "מצב רוח, לחץ ורווחה רגשית",
    "personal_growth": "צמיחה אישית",
}

LABEL_EN: Dict[str, str] = {
    "goals": "achieving goals",
    "parenting": "parenting",
    "relationships": "relationships and couples",
    "career": "career and work",
    "wellbeing": "stress and emotional wellbeing",
    "personal_growth": "personal growth",
}


def _normalize_topic_ids(prefs: Dict[str, Any]) -> List[str]:
    if prefs.get("bsd_topics_skipped"):
        return []
    raw = prefs.get("bsd_onboard_topics")
    ids: List[str] = []
    if isinstance(raw, list):
        ids = [
            str(x).strip()
            for x in raw
            if isinstance(x, str) and str(x).strip() in TOPIC_IDS
        ]
    if not ids:
        one = prefs.get("bsd_onboard_topic")
        if isinstance(one, str) and one.strip() in TOPIC_IDS:
            ids = [one.strip()]
    return ids


def build_onboarding_topics_hint(prefs: Dict[str, Any], language: str) -> Optional[str]:
    """
    Instruction block for the LLM (not shown directly to user).
    Only built when intake recorded one or more topic ids and user did not skip topics.
    """
    lang = (language or "he").lower()
    ids = _normalize_topic_ids(prefs)
    if not ids:
        return None

    labels = [LABEL_HE[i] if lang.startswith("he") else LABEL_EN[i] for i in ids]
    if lang.startswith("he"):
        if len(labels) == 1:
            listed = labels[0]
        elif len(labels) == 2:
            listed = f"{labels[0]} ו{labels[1]}"
        else:
            listed = ", ".join(labels[:-1]) + f", וגם {labels[-1]}"
        return (
            f"במהלך הקליטה המשתמש/ת סימן/ה שהתחומים הבאים מרגישים רלוונטיים עבורו/ה: {listed}.\n"
            "**כשאתה נותן את פתיחת שלב המצוי (S2)** — הנוסח שמסביר את המעבר לאירוע עם מגע בין-אישי — "
            "מותר **משפט קצר וחם אחד בלבד** (לפני או אחרי ההסבר הקבוע) שמקשר בעדינות למה שסימנת בפתיחה לגבי התחומים האלה, בלי לחץ ומבלי לדרוש שהאירוע ייגזר מהתחומים האלה. "
            "אחר כך המשך מיד בנוסח הרגיל של S2.\n"
            "**אל תחזור** על משפט כזה בשאר החילופים ב-S2. אם כבר הזכרת בתגובה קודמת בשיחה את תחומי הקליטה — אל תחזור."
        )

    if len(labels) == 1:
        listed = labels[0]
    elif len(labels) == 2:
        listed = f"{labels[0]} and {labels[1]}"
    else:
        listed = ", ".join(labels[:-1]) + f", and {labels[-1]}"
    return (
        f"During intake the coachee marked these areas as relevant: {listed}.\n"
        "**When you deliver the standard S2 opening** (into \"present reality\" / a concrete event with interpersonal contact), "
        "you **may add one short warm sentence only** — before or after the usual framing — that gently connects back to what they highlighted during onboarding about these areas. "
        "Do not imply the event must come from those areas. Then continue with the normal S2 script.\n"
        "**Do not repeat** this acknowledgement in later S2 turns. If you already mentioned it earlier in the conversation, skip it."
    )


def inject_onboarding_topics_into_state(state: Dict[str, Any], prefs: Dict[str, Any], language: str) -> None:
    """Merge prefs-derived hint into V2 state (mutates ``state``)."""
    hint = build_onboarding_topics_hint(prefs or {}, language)
    if hint:
        state["coach_context_onboarding_topics"] = hint
    else:
        state.pop("coach_context_onboarding_topics", None)
