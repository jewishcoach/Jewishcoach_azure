"""
Deep Psychological Analyzer — Cross-conversation profile insights.

Analyzes ALL of a user's conversations to surface:
  1. Language depth (concreteness, metaphor, nuance)
  2. Emotional expression (richness, avoided emotions)
  3. Engagement pattern (trend across sessions)
  4. Psychological blocks (externalization, minimization, avoidance, etc.)
  5. Core beliefs (implicit, derived from recurring language)
  6. Coping style
  7. Self-agency (internal vs. external locus of control)
  8. Growth trajectory (changes between early and recent sessions)

This runs ONLY when the user explicitly grants consent.
Result is cached in User.preferences["last_analysis"] for 7 days.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ─── Pydantic output schema ────────────────────────────────────────────────────

class IdentifiedBlock(BaseModel):
    name: str = Field(description="שם החסם: 'חיצוניות', 'מינימיזציה', 'הכחשה' וכד'")
    description: str = Field(description="פרשנות חמה, לא שיפוטית")
    quote: str = Field(description="ציטוט ישיר מהשיחות")
    frequency: int = Field(default=1, description="כמה פעמים זוהה")


class CoreBelief(BaseModel):
    belief: str = Field(description="האמונה כפי שניסחה: 'אני לא מספיק...'")
    evidence: List[str] = Field(default_factory=list, description="2-3 ציטוטים שתומכים")
    stage: str = Field(default="", description="שלב BSD שממנו עלה (S1-S12)")


class GrowthPoint(BaseModel):
    area: str = Field(description="תחום הצמיחה")
    early_example: str = Field(description="ניסוח/עמדה בשיחות הראשונות")
    recent_example: str = Field(description="ניסוח/עמדה בשיחות האחרונות")
    direction: str = Field(description="positive | stagnant | negative")


class DeepProfileInsights(BaseModel):
    generated_at: str = Field(description="ISO timestamp")
    conversations_analyzed: int
    total_user_words: int

    # 1. Language depth
    language_depth_score: float = Field(ge=0.0, le=1.0)
    language_examples: List[str] = Field(default_factory=list, description="2-3 ציטוטים ממחישים")
    language_depth_note: str = Field(default="")

    # 2. Emotional expression
    emotional_richness_score: float = Field(ge=0.0, le=1.0)
    frequent_emotions: List[str] = Field(default_factory=list)
    avoided_emotions: List[str] = Field(default_factory=list)
    emotional_note: str = Field(default="")

    # 3. Engagement pattern
    engagement_trend: str = Field(description="rising | stable | declining")
    engagement_note: str = Field(default="")

    # 4. Psychological blocks
    psychological_blocks: List[IdentifiedBlock] = Field(default_factory=list)

    # 5. Core beliefs
    core_beliefs: List[CoreBelief] = Field(default_factory=list)

    # 6. Coping style
    coping_style: str = Field(description="שם הסגנון")
    coping_description: str = Field(default="")

    # 7. Self-agency
    self_agency_score: float = Field(ge=0.0, le=1.0, description="0=חיצוני לגמרי, 1=פנימי לגמרי")
    agency_examples: List[str] = Field(default_factory=list)

    # 8. Growth trajectory
    growth_points: List[GrowthPoint] = Field(default_factory=list)

    # Summary
    summary: str = Field(description="פסקת פורטרט אישי (3-4 משפטים)")
    key_insight: str = Field(description="התובנה האחת החזקה ביותר")
    one_invitation: str = Field(description="הזמנה מעשית אחת להמשך הדרך")


# ─── System prompt ─────────────────────────────────────────────────────────────

ANALYSIS_SYSTEM_PROMPT = """אתה פסיכולוג קליני-קוגניטיבי בעל ניסיון רב בניתוח שיח טיפולי.
המשתמש הסכים מפורשות לניתוח זה ומבין שמדובר בבינה מלאכותית ולא באבחנה קלינית.

תפקידך: לנתח את השיחות ולהחזיר JSON תקני בלבד (ללא טקסט מסביב).

כללי הזהב:
• ציטוטים ישירים מהטקסט בכל ממד — לא המצאות
• שפה חמה, כבוד מלא, ללא שיפוטיות
• תובנה = מה שהמשתמש כבר יודע אבל עדיין לא ניסח
• אסור לנסח "אתה..." — רק "נדמה שיש...", "עולה תחושה של..."
• הימנע מאבחנות קליניות או תיוגים
"""

ANALYSIS_HUMAN_TEMPLATE = """=== נתונים מ-{n_conversations} שיחות אימון ===

--- נתונים מובנים (collected_data לפי שלבים) ---
{structured_json}

--- טקסט גולמי — הודעות המשתמש בלבד ---
{raw_messages}

=== הוראות ===
החזר JSON תקני בלבד, לפי הסכמה הזו (ללא שדות נוספים):
{{
  "generated_at": "<ISO timestamp>",
  "conversations_analyzed": <int>,
  "total_user_words": <int>,

  "language_depth_score": <0.0-1.0>,
  "language_examples": ["<ציטוט>", "<ציטוט>"],
  "language_depth_note": "<משפט פרשנות>",

  "emotional_richness_score": <0.0-1.0>,
  "frequent_emotions": ["<רגש>", ...],
  "avoided_emotions": ["<רגש>", ...],
  "emotional_note": "<משפט פרשנות>",

  "engagement_trend": "rising|stable|declining",
  "engagement_note": "<משפט>",

  "psychological_blocks": [
    {{"name": "<שם>", "description": "<פרשנות>", "quote": "<ציטוט>", "frequency": <int>}}
  ],

  "core_beliefs": [
    {{"belief": "<אמונה>", "evidence": ["<ציטוט>"], "stage": "<S1-S12>"}}
  ],

  "coping_style": "<שם הסגנון>",
  "coping_description": "<תיאור>",

  "self_agency_score": <0.0-1.0>,
  "agency_examples": ["<ציטוט>", ...],

  "growth_points": [
    {{"area": "<תחום>", "early_example": "<ניסוח ישן>", "recent_example": "<ניסוח חדש>", "direction": "positive|stagnant|negative"}}
  ],

  "summary": "<פסקת פורטרט 3-4 משפטים>",
  "key_insight": "<התובנה האחת החזקה>",
  "one_invitation": "<הזמנה מעשית>"
}}
"""


# ─── Main analyzer function ────────────────────────────────────────────────────

async def run_deep_analysis(
    conversations_data: List[Dict[str, Any]],
) -> DeepProfileInsights:
    """
    Run the deep psychological analysis on a user's conversations.

    Args:
        conversations_data: List of dicts, each with:
            - "collected_data": dict from v2_state
            - "user_messages": list of str (user-only message texts)
            - "message_count": int
    Returns:
        DeepProfileInsights pydantic object
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
        structured_json=structured_json[:6000],   # cap to avoid token overflow
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

    return DeepProfileInsights(**data)
