"""
"המבט שלי עליך" — Beni's personal letter at the end of the journey.

Generates a warm, narrative letter from the coach character ("Beni")
based on ALL of the user's conversations. Not a clinical analysis —
a personal gift that weaves personality observations into a letter.

Runs ONLY when user grants consent. Cached in User.preferences["last_analysis"].
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ─── Pydantic output schema ────────────────────────────────────────────────────

class JourneyMilestone(BaseModel):
    stage_name: str = Field(description="שם השלב: זיהוי, גילוי, כמ״ז, בחירה, חזון")
    what_emerged: str = Field(description="מה עלה בשלב הזה — משפט אחד בשפת בני")
    user_quote: str = Field(default="", description="ציטוט ישיר מהמשתמש בשלב הזה")


class DeepViewLetter(BaseModel):
    generated_at: str = Field(description="ISO timestamp")
    conversations_analyzed: int
    total_user_words: int

    # 1. המכתב מבני (כולל ניתוח אישיות)
    letter: str = Field(description="מכתב אישי מבני — 6-10 משפטים. פתיחה חמה, ניתוח אישיות בגוף המכתב, סיום עם גאווה")

    # 2. מה גילית על עצמך (סיכום המסע)
    journey_milestones: List[JourneyMilestone] = Field(default_factory=list, description="אבן דרך לכל שלב שהמשתמש עבר")

    # 3. מילה אחרונה
    closing_word: str = Field(description="משפט סיום חם + הזמנה להמשיך לגדול")


# ─── System prompt ─────────────────────────────────────────────────────────────

ANALYSIS_SYSTEM_PROMPT = """אתה "בני", מאמן אישי חם ואבהי. סיימת מסע אימון ארוך עם המתאמן שלך.
עכשיו אתה כותב לו מכתב אישי — מתנה בסוף המסע.

המכתב הזה הוא הרגע שבו אתה אומר לו: "ראיתי אותך. הנה מה שראיתי."

כללי הכתיבה:
• כתוב כאילו אתה מדבר אליו פנים אל פנים — חם, ישיר, בגובה העיניים
• השתמש בציטוטים ישירים מהשיחות — "כשאמרת '...', הבנתי ש..."
• אל תתייג ואל תאבחן. אל תשתמש במונחים כמו "חסם", "מוקד שליטה", "סגנון התמודדות"
• במקום ציונים ומדדים — ספר מה ראית. "שמתי לב ש...", "ראיתי איך..."
• הניתוח האישיותי שזור בתוך המכתב, לא כסעיף נפרד
• חתום "— בני"

טון: כמו אבא חכם שיושב מולך ואומר לך מי אתה באמת. לא מתנשא, לא מחמיא סתם — אמיתי.

החזר JSON תקני בלבד (ללא טקסט מסביב).
"""

ANALYSIS_HUMAN_TEMPLATE = """=== נתונים מ-{n_conversations} שיחות אימון ===

--- נתונים מובנים (collected_data לפי שלבים) ---
{structured_json}

--- טקסט גולמי — הודעות המשתמש בלבד ---
{raw_messages}

=== הוראות ===
כתוב את "המבט שלי עליך" — המתנה שלך למתאמן בסיום המסע.

החזר JSON תקני בלבד, לפי הסכמה הזו:
{{
  "generated_at": "<ISO timestamp>",
  "conversations_analyzed": <int>,
  "total_user_words": <int>,

  "letter": "<מכתב אישי מבני. 6-10 משפטים. מבנה: פתיחה חמה ('עברנו יחד דרך...') → מה ראית בו כאדם (ניתוח אישיות שזור בתוך המכתב, לא כרשימה) → ציטוטים מהשיחות שמדגימים → סיום עם גאווה. חתום: — בני>",

  "journey_milestones": [
    {{
      "stage_name": "<שם השלב: זיהוי / גילוי / כמ״ז / בחירה / חזון>",
      "what_emerged": "<מה עלה — משפט אחד בשפה של בני, לא תיאור טכני>",
      "user_quote": "<ציטוט ישיר מהמשתמש בשלב הזה, אם יש>"
    }}
  ],

  "closing_word": "<משפט סיום חם. הזמנה להמשיך לגדול + רמז עדין שיש עוד מה לגלות (בספר, בחיים, בדרך). לא מכירתי — חם.>"
}}

דוגמה לטון הנכון במכתב:
"עברנו יחד כמה חודשים, ואני רוצה לספר לך מה ראיתי. אתה בן אדם שמרגיש עמוק אבל רגיל להסתיר את זה מאחורי הומור. כשאמרת 'אני תמיד האחד שמחזיק את כולם' — הבנתי שאתה נושא הרבה, ולפעמים שוכח שגם אתה צריך מישהו שיחזיק אותך..."
"""


# ─── Main analyzer function ────────────────────────────────────────────────────

async def run_deep_analysis(
    conversations_data: List[Dict[str, Any]],
) -> DeepViewLetter:
    """
    Generate Beni's personal letter — the "gift" at the end of the journey.

    Args:
        conversations_data: List of dicts, each with:
            - "collected_data": dict from v2_state
            - "user_messages": list of str (user-only message texts)
            - "message_count": int
    Returns:
        DeepViewLetter pydantic object
    """
    from ..bsd.llm import get_azure_chat_llm

    n = len(conversations_data)

    # Build structured JSON summary
    structured_parts = []
    all_user_texts: List[str] = []
    total_words = 0

    for i, conv in enumerate(conversations_data, 1):
        cd = conv.get("collected_data") or {}
        msgs = conv.get("user_messages") or []
        structured_parts.append(f"שיחה {i}: {json.dumps(cd, ensure_ascii=False, indent=2)}")
        for msg in msgs:
            if msg and msg.strip():
                all_user_texts.append(msg.strip())
                total_words += len(msg.split())

    structured_json = "\n\n".join(structured_parts)
    raw_messages = "\n---\n".join(all_user_texts)

    human_text = ANALYSIS_HUMAN_TEMPLATE.format(
        n_conversations=n,
        structured_json=structured_json[:6000],
        raw_messages=raw_messages[:8000],
    )

    llm = get_azure_chat_llm(purpose="reasoner")
    messages = [
        SystemMessage(content=ANALYSIS_SYSTEM_PROMPT),
        HumanMessage(content=human_text),
    ]

    response = await llm.ainvoke(messages)
    raw_text = response.content.strip()

    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        raw_text = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    data = json.loads(raw_text)

    # Ensure required timestamps
    if not data.get("generated_at"):
        data["generated_at"] = datetime.now(timezone.utc).isoformat()
    data["conversations_analyzed"] = n
    data["total_user_words"] = total_words

    return DeepViewLetter(**data)
