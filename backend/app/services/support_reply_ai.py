"""Generate customer-support email drafts (Azure OpenAI), aligned with admin-configured tone/policy."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..bsd.llm import get_azure_chat_llm_4o_mini

_JSON_FENCE = re.compile(r"^```(?:json)?\s*", re.I)
_JSON_FENCE_END = re.compile(r"\s*```\s*$", re.I)


class SupportDraftReplyResult(BaseModel):
    subject: str = Field(default="", max_length=480)
    body_plain: str = ""
    internal_notes: Optional[str] = None


def _parse_llm_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    text = _JSON_FENCE.sub("", text)
    text = _JSON_FENCE_END.sub("", text).strip()
    return json.loads(text)


DEFAULT_METHODOLOGY_HE = """Jewish Coach היא אפליקציית קואצ'ינג בעברית עם גישה יהודית־ערכית (כבוד, צניעות, מעשה במידה).
המערכת משלבת שיחה עם מאמן AI לפי תהליך מובנה (שלבים S0–S10 / BSD), יומן אימון וכלים לעבודה עצמית.
אין להציג את עצמך כרופא/עורך דין/מטפל קליני; הפנה לגורם מקצועי כשיש חשש בריאותי או משפטי."""

DEFAULT_METHODOLOGY_EN = """Jewish Coach is a Hebrew-first coaching web app with respectful Jewish-values framing.
It combines structured AI coaching (phased methodology), journaling, and self-work tools.
Do not present as a clinician or lawyer; recommend professional help when appropriate."""


def generate_support_reply_draft(
    *,
    customer_snapshot: dict[str, Any],
    incoming_message: str,
    personality_text: Optional[str],
    terms_text: Optional[str],
    methodology_text: Optional[str],
    language: str = "he",
) -> SupportDraftReplyResult:
    lang = (language or "he").lower()
    methodology_block = (methodology_text or "").strip()
    if not methodology_block:
        methodology_block = DEFAULT_METHODOLOGY_HE if lang.startswith("he") else DEFAULT_METHODOLOGY_EN

    personality_block = (personality_text or "").strip() or (
        "טון חם, מכבד וקצר; עניין אמיתי בפתרון הבעיה." if lang.startswith("he") else "Warm, concise, respectful."
    )
    terms_block = (terms_text or "").strip() or (
        "אל תמציא החזרים/קופונים/זכאות שלא מופיעים בנתוני המשתמש. אם אין מידע — הצע לבדוק באפליקציה או לחבר צוות."
        if lang.startswith("he")
        else "Do not invent refunds, coupons, or eligibility not shown in user facts. Offer next steps if uncertain."
    )

    if lang.startswith("he"):
        sys_msg = f"""אתה נציג שירות לקוחות של Jewish Coach (כתובת תמיכה: support@jewishcoacher.com).
ענה כמו אימייל רשמי ונעים ללקוח.

החזר אך ורק JSON תקין עם המפתחות:
- "subject" (שורת נושא קצרה)
- "body_plain" (גוף תשובה כטקסט רב־שורות; ללא Markdown מורכב)
- "internal_notes" (אופציונלי — הערות פנימיות לצוות, לא לשליחה ללקוח)

כללי אישיות והטון:
{personality_block}

גבולות ותנאי שירות (חובה לציית):
{terms_block}

הקשר מוצר ושיטה:
{methodology_block}

כללי נתונים:
- השתמש רק במידע על המשתמש שמופיע ב־JSON המצורף (customer_snapshot).
- אם המשתמש לא נמצא במערכת — הסבר בעדינות שאולי נרשם עם מייל אחר, ובקש פרטים לאימות בלי לחשוף מידע על משתמשים אחרים.
"""
    else:
        sys_msg = f"""You are Jewish Coach customer support (support@jewishcoacher.com). Reply as a polished support email.

Return ONLY valid JSON with keys subject, body_plain, optional internal_notes.

Voice / personality:
{personality_block}

Policies / boundaries:
{terms_block}

Product & methodology context:
{methodology_block}

Use ONLY facts from the attached customer_snapshot JSON. If no user match, explain gently and ask for details without leaking other users' data.
"""

    human = json.dumps({"customer_snapshot": customer_snapshot, "customer_message": incoming_message.strip()}, ensure_ascii=False)

    llm = get_azure_chat_llm_4o_mini()
    resp = llm.invoke([SystemMessage(content=sys_msg), HumanMessage(content=human)])
    raw_text = (resp.content or "").strip()
    data = _parse_llm_json(raw_text)
    return SupportDraftReplyResult.model_validate(data)

