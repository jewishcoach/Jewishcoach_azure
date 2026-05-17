"""
Deterministic coach copy for POST /api/onboarding/intake/step.

The LLM must never author these strings — only slot extraction runs through the model.
"""

from __future__ import annotations


def intake_closing(language: str) -> str:
    lang = (language or "he").lower()
    if lang.startswith("he"):
        return "מעולה. עכשיו אפשר לבחור את נושא האימון מהכרטיסים למטה."
    return "Great — pick your coaching focus from the cards below."


def intake_ask_name_first(language: str) -> str:
    lang = (language or "he").lower()
    if lang.startswith("he"):
        return "נשמח להכיר — איך נוח לך שנפנה אליך? (אפשר גם בלי שם.)"
    return "How would you like us to address you? (A name is optional.)"


def intake_ask_name_redirect(language: str) -> str:
    """User already replied without resolving name — short redirect."""
    lang = (language or "he").lower()
    if lang.startswith("he"):
        return "כדי שנמשיך בקליטה: איך נוח לך שנפנה אליך? (אפשר בלי שם.)"
    return "To continue onboarding: how should we address you? (You can skip a name.)"


def intake_ask_gender(language: str) -> str:
    lang = (language or "he").lower()
    if lang.startswith("he"):
        return (
            "כדי לנסח בעברית בצורה טבעית — בחר/י למטה זכר או נקבה, "
            "או כתוב במילים (זכר/גבר או נקבה/אישה)."
        )
    return "Please tap Male or Female below, or type male / female."


def intake_ask_topic(language: str, gender: str) -> str:
    lang = (language or "he").lower()
    if lang.startswith("he"):
        if gender == "female":
            return "מעולה. עכשיו תוכלי לבחור את נושא האימון מהכרטיסים למטה."
        return "מעולה. עכשיו תוכל לבחור את נושא האימון מהכרטיסים למטה."
    if gender == "female":
        return "Great — now pick your coaching focus from the cards below."
    return "Great — now pick your coaching focus from the cards below."


def pick_intake_assistant_message(
    language: str,
    *,
    missing: str,
    gender: str | None,
    user_message_count: int,
) -> str:
    """
    :param missing: display_name | gender | topic (must not be complete).
    """
    if missing == "display_name":
        if user_message_count >= 2:
            return intake_ask_name_redirect(language)
        return intake_ask_name_first(language)
    if missing == "gender":
        return intake_ask_gender(language)
    if missing == "topic":
        if gender in ("male", "female"):
            return intake_ask_topic(language, gender)
        return intake_ask_gender(language)
    return intake_closing(language)
