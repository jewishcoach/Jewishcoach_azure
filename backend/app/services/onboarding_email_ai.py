"""LLM-assisted onboarding email step drafts (Azure OpenAI)."""

from __future__ import annotations

import json
import re
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..bsd.llm import get_azure_chat_llm_4o_mini


class DraftEmailAIResult(BaseModel):
    subject: str = Field(default="", max_length=480)
    body_html: str = ""
    body_plain: Optional[str] = None


_JSON_FENCE = re.compile(r"^```(?:json)?\s*", re.I)
_JSON_FENCE_END = re.compile(r"\s*```\s*$", re.I)


def _parse_llm_json(raw: str) -> dict:
    text = (raw or "").strip()
    text = _JSON_FENCE.sub("", text)
    text = _JSON_FENCE_END.sub("", text).strip()
    return json.loads(text)


SYSTEM_PROMPT_HE = """אתה קופירייטר מוביל למוצר "Jewish Coach" — אפליקציית אימון וקואצ'ינג בעברית (גישה יהודית־ערכית, מכבדת וחמה).
החזר אך ורק JSON תקין עם המפתחות:
- "subject" (שורת נושא, קצרה)
- "body_html" (גוף במבנה HTML, טון חם ומקצועי, קריא לפעולה להיכנס לאפליקציה ולהמשיך בתהליך האימון)
- "body_plain" (אופציונלי — טקסט פשוט ללא תגיות)

אסור להמציא הנחות מחיר או קופונים אלא אם התבקש במפורש. השתמש ב-{{display_name}} וב-{{app_url}} במקום פרטים אישיים."""

SYSTEM_PROMPT_EN = """You are a lifecycle email copywriter for "Jewish Coach", a Hebrew-first Jewish-values coaching web app.
Return ONLY valid JSON with keys subject, body_html, optional body_plain.
Use placeholders {{display_name}} and {{app_url}} where greets/links are needed.
Tone: warm, respectful, motivating to open the app and continue coaching.
Do not invent coupons/pricing unless explicitly requested in the user brief."""


def generate_onboarding_step_draft(
    *,
    admin_prompt: str,
    language: str = "he",
    sequence_name: Optional[str] = None,
    step_position: Optional[int] = None,
    previous_subjects: Optional[list[str]] = None,
) -> DraftEmailAIResult:
    lang = (language or "he").lower()
    sys_msg = SYSTEM_PROMPT_HE if lang.startswith("he") else SYSTEM_PROMPT_EN

    ctx_parts: list[str] = []
    if sequence_name:
        ctx_parts.append(f"שם הסדרה / Sequence: {sequence_name}")
    if step_position is not None:
        ctx_parts.append(f"מספר מסר בשרשרת / Step index (1-based): {step_position}")
    if previous_subjects:
        ctx_parts.append("נושאים קודמים בשרשרת / Previous subjects:\n- " + "\n- ".join(previous_subjects[:8]))

    human = (admin_prompt or "").strip()
    if not human:
        raise ValueError("admin_prompt is empty")

    full_human = "\n".join(ctx_parts + ["", "הוראות מהמנהל / Admin brief:", human])

    llm = get_azure_chat_llm_4o_mini()
    resp = llm.invoke([SystemMessage(content=sys_msg), HumanMessage(content=full_human)])
    raw_text = (resp.content or "").strip()
    data = _parse_llm_json(raw_text)
    return DraftEmailAIResult.model_validate(data)
