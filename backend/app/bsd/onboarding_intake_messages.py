"""
Deterministic coach copy for POST /api/onboarding/intake/step.

Warm, first-person coach voice — not admin/bot tone. LLM only extracts slots.
"""

from __future__ import annotations


def intake_closing(language: str) -> str:
    lang = (language or "he").lower()
    if lang.startswith("he"):
        return "מעולה, תודה ששיתפת."
    return "Thank you for sharing that."


def intake_ask_name_first(language: str) -> str:
    lang = (language or "he").lower()
    if lang.startswith("he"):
        return (
            "היי, טוב לראות אותך פה.\n\n"
            "לפני שנצלול — איך נוח לך שאפנה אליך? אם נוח יותר בלי שם — זה גם לגמרי בסדר."
        )
    return (
        "Hey — glad you're here.\n\n"
        "Before we ease in: what should I call you? And if you'd rather skip a name, that's completely fine."
    )


def intake_ask_name_redirect(language: str) -> str:
    """User already replied without resolving name — gentle redirect."""
    lang = (language or "he").lower()
    if lang.startswith("he"):
        return (
            "נשארתי רגע עם השאלה הזו כדי שנוכל להמשיך ברוגע.\n\n"
            "איך נוח לך שאצור איתך קשר — בשם או בלי?"
        )
    return (
        "I'll stay with this for a moment so we can move forward calmly.\n\n"
        "How would you like me to relate to you — with a name, or without?"
    )


def intake_ask_gender(language: str) -> str:
    lang = (language or "he").lower()
    if lang.startswith("he"):
        return (
            "מה המגדר שלך?\n\n"
            "אין חובה לשתף — רק כדי שאוכל להתאים את הניסוח. "
            "אפשר לבחור למטה, לכתוב במילים, או ללחוץ על «לא רוצה לשתף»."
        )
    return (
        "What's your gender? You're welcome not to share — it only helps me phrase things naturally. "
        "Pick below, type it in your own words, or tap “Prefer not to say.”"
    )


def intake_ask_gender_after_name(language: str, display_name: str) -> str:
    """Right after the coachee shared their name — greet by name, then ask grammatical gender."""
    name = (display_name or "").strip()
    if not name:
        return intake_ask_gender(language)
    lang = (language or "he").lower()
    if lang.startswith("he"):
        return (
            f"שלום {name}, נעים להכיר!\n\n"
            "איך לפנות אליך — בלשון זכר או נקבה?\n\n"
            "אפשר לבחור למטה, לכתוב במילים, או ללחוץ על «לא רוצה לשתף»."
        )
    return (
        f"Hello {name}, lovely to meet you!\n\n"
        "How should I address you — masculine or feminine?\n\n"
        "Pick below, type it in your own words, or tap “Prefer not to say.”"
    )


def intake_ask_topic(language: str, gender: str) -> str:
    """gender kept for API stability; copy is neutral (multi-select + optional)."""
    lang = (language or "he").lower()
    if lang.startswith("he"):
        return (
            "מצוין.\n\n"
            "אם בא לך — אפשר לסמן נושא אחד או יותר שמרגישים רלוונטיים; "
            "זה לא מחייב את מהלך האימון, רק עוזר לי להכיר אתכם טוב יותר. "
            "אפשר גם לדלג ולהמשיך בלי."
        )
    return (
        "Great.\n\n"
        "If you'd like, choose one or more focus areas — nothing here locks us into a path; "
        "it simply helps me know you a little better. You can also skip and continue without choosing."
    )


def pick_intake_assistant_message(
    language: str,
    *,
    missing: str,
    gender: str | None,
    user_message_count: int,
    gender_skipped: bool = False,
    display_name: str | None = None,
) -> str:
    """
    :param missing: display_name | gender | topic (must not be complete).
    """
    if missing == "display_name":
        if user_message_count >= 2:
            return intake_ask_name_redirect(language)
        return intake_ask_name_first(language)
    if missing == "gender":
        dn = (display_name or "").strip()
        if dn:
            return intake_ask_gender_after_name(language, dn)
        return intake_ask_gender(language)
    if missing == "topic":
        if gender in ("male", "female") or gender_skipped:
            return intake_ask_topic(language, gender or "")
        return intake_ask_gender(language)
    return intake_closing(language)
