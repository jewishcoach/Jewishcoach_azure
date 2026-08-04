"""
BSD V2 - Stage Intro Question Generator & Stage Summary Builder.

Generates contextual intro questions for macro-stage transitions using gpt-4o-mini.
Also produces rule-based stage summaries from collected_data.
"""

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from ..bsd.llm import get_azure_chat_llm_4o_mini
from .stage_intro_schema import (
    MACRO_STAGES,
    IntroAnswerOption,
    IntroQuestion,
    StageIntroPayload,
    StageSummaryPayload,
    get_macro_stage,
    next_macro_stage,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stage summary generation (rule-based from collected_data)
# ---------------------------------------------------------------------------

def generate_stage_summary(
    state: dict[str, Any],
    completed_macro_id: str,
    language: str = "he",
) -> StageSummaryPayload:
    """
    Build a summary for a completed macro-stage from collected_data.
    No LLM call — purely rule-based extraction.
    """
    macro = get_macro_stage(completed_macro_id)
    if not macro:
        raise ValueError(f"Unknown macro-stage: {completed_macro_id}")

    collected = state.get("collected_data", {})
    is_he = language.startswith("he")
    title = macro["title_he"] if is_he else macro["title_en"]

    insights = _extract_insights(collected, completed_macro_id, is_he)

    next_id = next_macro_stage(completed_macro_id)
    next_macro = get_macro_stage(next_id) if next_id else None

    return StageSummaryPayload(
        stage_id=completed_macro_id,
        stage_title=title,
        insights=insights,
        next_stage_id=next_id,
        next_stage_title=(
            (next_macro["title_he"] if is_he else next_macro["title_en"])
            if next_macro
            else None
        ),
    )


def _extract_insights(
    collected: dict[str, Any], macro_id: str, is_he: bool
) -> list[str]:
    """Extract 2-4 insight strings from collected_data based on macro-stage."""
    insights: list[str] = []

    if macro_id == "identification":
        if collected.get("topic"):
            insights.append(
                f"הנושא שלך: {collected['topic']}" if is_he
                else f"Your topic: {collected['topic']}"
            )
        if collected.get("emotions"):
            emotions_str = ", ".join(collected["emotions"][:4])
            insights.append(
                f"הרגשות שזיהית: {emotions_str}" if is_he
                else f"Emotions identified: {emotions_str}"
            )
        if collected.get("thought"):
            insights.append(
                f"המחשבה הפנימית: \"{collected['thought']}\"" if is_he
                else f"Inner thought: \"{collected['thought']}\""
            )
        if collected.get("pattern"):
            insights.append(
                f"הדפוס שחוזר: {collected['pattern']}" if is_he
                else f"Recurring pattern: {collected['pattern']}"
            )
        if collected.get("gap_name"):
            gap_str = collected["gap_name"]
            if collected.get("gap_score"):
                gap_str += f" ({collected['gap_score']}/10)"
            insights.append(
                f"הפער: {gap_str}" if is_he else f"The gap: {gap_str}"
            )

    elif macro_id == "discovery":
        if collected.get("paradigm"):
            insights.append(
                f"הפרדיגמה: \"{collected['paradigm']}\"" if is_he
                else f"Paradigm: \"{collected['paradigm']}\""
            )
        stance = collected.get("stance") or {}
        if stance.get("reality_belief"):
            insights.append(
                f"העמדה: \"{stance['reality_belief']}\"" if is_he
                else f"Stance: \"{stance['reality_belief']}\""
            )
        if stance.get("gains"):
            insights.append(
                f"רווחים מהדפוס: {', '.join(stance['gains'][:3])}" if is_he
                else f"Gains from pattern: {', '.join(stance['gains'][:3])}"
            )
        if stance.get("losses"):
            insights.append(
                f"הפסדים מהדפוס: {', '.join(stance['losses'][:3])}" if is_he
                else f"Losses from pattern: {', '.join(stance['losses'][:3])}"
            )

    elif macro_id == "kamaz":
        forces = collected.get("forces") or {}
        if forces.get("source"):
            insights.append(
                f"כוחות מקור: {', '.join(forces['source'][:3])}" if is_he
                else f"Source forces: {', '.join(forces['source'][:3])}"
            )
        if forces.get("nature"):
            insights.append(
                f"כוחות טבע: {', '.join(forces['nature'][:3])}" if is_he
                else f"Nature forces: {', '.join(forces['nature'][:3])}"
            )

    elif macro_id == "choice":
        if collected.get("renewal"):
            insights.append(
                f"הבחירה החדשה: \"{collected['renewal']}\"" if is_he
                else f"New choice: \"{collected['renewal']}\""
            )

    elif macro_id == "vision":
        if collected.get("vision"):
            insights.append(
                f"החזון: \"{collected['vision']}\"" if is_he
                else f"Vision: \"{collected['vision']}\""
            )
        if collected.get("commitment"):
            insights.append(
                f"ההתחייבות: \"{collected['commitment']}\"" if is_he
                else f"Commitment: \"{collected['commitment']}\""
            )

    if not insights:
        insights.append(
            "סיימת את השלב הזה בהצלחה" if is_he
            else "You completed this stage successfully"
        )

    return insights[:4]


# ---------------------------------------------------------------------------
# Intro question generation (LLM-based, contextual)
# ---------------------------------------------------------------------------

INTRO_SYSTEM_PROMPT_HE = """\
אתה עוזר ליצור שאלות פתיחה מובנות לשלב חדש בתהליך אימון BSD.
המטרה: ליצור 1-3 שאלות עם 4-6 אפשרויות תשובה לכל שאלה.
השאלות והתשובות חייבות להיות בהתאם להקשר של השיחה — מתייחסות לנושא, לרגשות, לאירועים שהמתאמן כבר שיתף.

כללים:
- שפה חמה, לא פורמלית, גובה עיניים
- אפשרויות התשובה צריכות לכסות מרחב רחב ומגוון (לא רק שליליות או רק חיוביות)
- תמיד כלול אפשרות "אחר" או "משהו אחר" כאופציה אחרונה
- השאלות צריכות להיות ספציפיות למה שהמתאמן סיפר, לא גנריות
- אל תחזור על מידע שכבר נאסף — התקדם קדימה
"""

INTRO_SYSTEM_PROMPT_EN = """\
You generate structured opening questions for a new stage in a BSD coaching process.
Goal: Create 1-3 questions with 4-6 answer options each.
Questions and answers must be contextual — referencing the topic, emotions, events the trainee already shared.

Rules:
- Warm, informal tone, eye-level
- Answer options should cover a broad, diverse range (not only negative or only positive)
- Always include "Something else" as the last option
- Questions should be specific to what the trainee shared, not generic
- Don't repeat already-collected information — move forward
"""

MACRO_STAGE_PROMPTS = {
    "discovery": {
        "he": "השלב הבא: גילוי — מגלה שיש דרך נוספת להסתכל על המציאות. מתמקד בפרדיגמה (\"ככה זה אצלי\"), עמדה (תפיסת המציאות), וטריגרים.",
        "en": "Next stage: Discovery — finding another way to see reality. Focus on paradigm ('that's how it is for me'), stance (reality perception), and triggers.",
    },
    "kamaz": {
        "he": "השלב הבא: כמ\"ז — כוחות מקור (נפש אלוקית: אור, ערכים, שליחות) וכוחות טבע (נפש טבעית: צרכים, הגנות, דחפים). בונים כרטיס אישי של 6+6 כוחות.",
        "en": "Next stage: Forces (KMZ) — Source forces (divine soul: light, values, mission) and Nature forces (natural soul: needs, defenses, impulses). Building a personal 6+6 card.",
    },
    "choice": {
        "he": "השלב הבא: בחירה — לעצב מחדש את הרצוי. עמדה חדשה, פרדיגמה חדשה, דפוס חדש. הכמ\"ז עוזר לנו לבחור מתוך מקום של מודעות.",
        "en": "Next stage: Choice — redesigning the desired. New stance, new paradigm, new pattern. The KMZ helps us choose from a place of awareness.",
    },
    "vision": {
        "he": "השלב הבא: חזון — לבחור את החיים שאני באמת רוצה לחיות. תמונת עתיד ומחויבות לצעד ראשון קונקרטי.",
        "en": "Next stage: Vision — choosing the life I truly want to live. Future picture and commitment to a concrete first step.",
    },
}


async def generate_stage_intro(
    state: dict[str, Any],
    target_macro_id: str,
    language: str = "he",
) -> StageIntroPayload:
    """
    Generate contextual intro questions for a target macro-stage.
    Uses gpt-4o-mini with structured output.
    """
    macro = get_macro_stage(target_macro_id)
    if not macro:
        raise ValueError(f"Unknown macro-stage: {target_macro_id}")

    is_he = language.startswith("he")
    collected = state.get("collected_data", {})

    system_prompt = INTRO_SYSTEM_PROMPT_HE if is_he else INTRO_SYSTEM_PROMPT_EN
    stage_context = MACRO_STAGE_PROMPTS.get(target_macro_id, {}).get(
        "he" if is_he else "en", ""
    )

    context_summary = _build_context_summary(collected, is_he)

    user_message = f"""{stage_context}

{"הנה מה שהמתאמן שיתף עד כה:" if is_he else "Here's what the trainee shared so far:"}
{context_summary}

{"צור 1-3 שאלות פתיחה מובנות לשלב הזה עם 4-6 אפשרויות תשובה לכל שאלה." if is_he else "Generate 1-3 structured opening questions for this stage with 4-6 answer options each."}"""

    llm = get_azure_chat_llm_4o_mini()
    structured_llm = llm.with_structured_output(
        StageIntroPayload, method="function_calling"
    )

    try:
        result = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ])
        if result and isinstance(result, StageIntroPayload):
            result.stage_id = target_macro_id
            result.stage_title = macro["title_he"] if is_he else macro["title_en"]
            return result
    except Exception:
        logger.exception("Failed to generate stage intro questions for %s", target_macro_id)

    return _fallback_intro(macro, target_macro_id, is_he)


def _build_context_summary(collected: dict[str, Any], is_he: bool) -> str:
    """Build a summary of collected_data for the LLM prompt."""
    parts: list[str] = []

    if collected.get("topic"):
        parts.append(f"{'נושא' if is_he else 'Topic'}: {collected['topic']}")
    if collected.get("event_description"):
        desc = collected["event_description"][:200]
        parts.append(f"{'אירוע' if is_he else 'Event'}: {desc}")
    if collected.get("emotions"):
        parts.append(f"{'רגשות' if is_he else 'Emotions'}: {', '.join(collected['emotions'])}")
    if collected.get("thought"):
        parts.append(f"{'מחשבה' if is_he else 'Thought'}: {collected['thought']}")
    if collected.get("action_actual"):
        parts.append(f"{'פעולה בפועל' if is_he else 'Actual action'}: {collected['action_actual']}")
    if collected.get("action_desired"):
        parts.append(f"{'רצוי' if is_he else 'Desired'}: {collected['action_desired']}")
    if collected.get("gap_name"):
        parts.append(f"{'פער' if is_he else 'Gap'}: {collected['gap_name']}")
    if collected.get("pattern"):
        parts.append(f"{'דפוס' if is_he else 'Pattern'}: {collected['pattern']}")
    if collected.get("paradigm"):
        parts.append(f"{'פרדיגמה' if is_he else 'Paradigm'}: {collected['paradigm']}")

    stance = collected.get("stance") or {}
    if stance.get("reality_belief"):
        parts.append(f"{'עמדה' if is_he else 'Stance'}: {stance['reality_belief']}")

    forces = collected.get("forces") or {}
    if forces.get("source"):
        parts.append(f"{'כוחות מקור' if is_he else 'Source forces'}: {', '.join(forces['source'][:3])}")
    if forces.get("nature"):
        parts.append(f"{'כוחות טבע' if is_he else 'Nature forces'}: {', '.join(forces['nature'][:3])}")

    if collected.get("renewal"):
        parts.append(f"{'בחירה חדשה' if is_he else 'New choice'}: {collected['renewal']}")

    return "\n".join(parts) if parts else ("אין מידע עדיין" if is_he else "No information yet")


def _fallback_intro(
    macro: dict, target_macro_id: str, is_he: bool
) -> StageIntroPayload:
    """Fallback intro when LLM call fails."""
    title = macro["title_he"] if is_he else macro["title_en"]
    return StageIntroPayload(
        stage_id=target_macro_id,
        stage_title=title,
        intro_text=(
            f"בוא נתחיל את שלב ה{title}"
            if is_he
            else f"Let's begin the {title} stage"
        ),
        questions=[
            IntroQuestion(
                id="q1",
                prompt=(
                    "מה אתה מרגיש לקראת השלב הזה?"
                    if is_he
                    else "How do you feel about this stage?"
                ),
                options=[
                    IntroAnswerOption(id="opt_1", label="סקרן" if is_he else "Curious"),
                    IntroAnswerOption(id="opt_2", label="מוכן" if is_he else "Ready"),
                    IntroAnswerOption(id="opt_3", label="חושש קצת" if is_he else "A bit apprehensive"),
                    IntroAnswerOption(id="opt_4", label="משהו אחר" if is_he else "Something else"),
                ],
                multi_select=False,
                allow_free_text=True,
            )
        ],
    )


def format_intro_answers_as_context(
    answers: dict[str, list[str]],
    questions: list[dict],
    language: str = "he",
) -> str:
    """
    Format the user's structured intro answers into a context string
    that can be injected into the conversation context for the LLM.
    """
    is_he = language.startswith("he")
    parts: list[str] = []

    question_map = {q["id"]: q for q in questions}

    for q_id, selected_option_ids in answers.items():
        q = question_map.get(q_id)
        if not q:
            continue
        option_map = {opt["id"]: opt["label"] for opt in q.get("options", [])}
        selected_labels = [
            option_map.get(opt_id, opt_id) for opt_id in selected_option_ids
        ]
        if selected_labels:
            parts.append(f"{q['prompt']} → {', '.join(selected_labels)}")

    if not parts:
        return ""

    header = "תשובות מובנות בכניסה לשלב:" if is_he else "Structured entry answers:"
    return f"{header}\n" + "\n".join(parts)
