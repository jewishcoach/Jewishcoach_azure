"""
Deterministic coach copy for POST /api/onboarding/intake/step.

Warm, first-person coach voice — not admin/bot tone. LLM only extracts slots.
"""

from __future__ import annotations


def intake_closing(language: str) -> str:
    lang = (language or "he").lower()
    if lang.startswith("he"):
        return (
            "מצוין.\n\n"
            "עכשיו רק לבחור מהכרטיסים למטה את נושא האימון שהכי מדבר אליך ברגע הזה — ומשם נמשיך."
        )
    return (
        "Lovely.\n\n"
        "Pick the coaching focus below that feels most alive for you right now — and we'll take it from there."
    )


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
            "יש לי עוד משהו קטן טכני בשביל הניסוח בעברית:\n\n"
            "זכר או נקבה? יש למטה גם כפתורים נוחים — ואפשר גם פשוט לכתוב במילים."
        )
    return (
        "One small practical detail so I can phrase things naturally:\n\n"
        "Male or female grammatical form? There are quick buttons below — or you can just type it."
    )


def intake_ask_topic(language: str, gender: str) -> str:
    lang = (language or "he").lower()
    if lang.startswith("he"):
        if gender == "female":
            return (
                "מצוין.\n\n"
                "עכשיו תני לעצמך רגע: מהכרטיסים למטה, מה מרגיש לך הכי רלוונטי לאימון כרגע? "
                "מזה נמשיך את השיחה."
            )
        return (
            "מצוין.\n\n"
            "עכשיו תן לעצמך רגע: מהכרטיסים למטה, מה מרגיש לך הכי רלוונטי לאימון כרגע? "
            "מזה נמשיך את השיחה."
        )
    if gender == "female":
        return (
            "Beautiful.\n\n"
            "Take a breath — which card below feels most like what you want coaching on right now? We'll go from there."
        )
    return (
        "Beautiful.\n\n"
        "Take a breath — which card below feels most like what you want coaching on right now? We'll go from there."
    )


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
