"""Azure OpenAI content-filter detection, retry, and user-facing fallback."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_CONTENT_FILTER_MARKERS = (
    "content management policy",
    "content_filter",
    "responsibleaipolicyviolation",
    "content filtering policies",
)


class ContentFilterBlockedError(Exception):
    """Azure OpenAI content management policy blocked coach response."""


def _filter_categories(err: BaseException) -> str:
    """Which filter fired ("jailbreak", "hate"…) — names only, never the content."""
    body = getattr(err, "body", None) or {}
    result = ((body.get("innererror") or {}).get("content_filter_result") or {}) if isinstance(body, dict) else {}
    hits = [k for k, v in result.items() if isinstance(v, dict) and (v.get("filtered") or v.get("detected"))]
    return ",".join(sorted(hits)) or "unknown"


def is_content_filter_error(err: BaseException) -> bool:
    text = str(err).lower()
    return any(marker in text for marker in _CONTENT_FILTER_MARKERS)


def content_filter_user_message(language: str) -> str:
    if language == "he":
        return (
            "נתקלתי במגבלה טכנית זמנית בשיחה. בוא ננסה להמשיך — "
            "אפשר לנסח את המחשבה בצורה קצרה יותר?"
        )
    return (
        "I hit a temporary safety limit. Let's continue — "
        "could you rephrase your last thought more briefly?"
    )


async def invoke_structured_coach_llm(
    structured_llm: Any,
    messages: list,
    *,
    context: str,
    system_prompt: str,
    language: str,
) -> dict:
    """Call structured LLM; on Azure content filter, retry once with trimmed context."""
    from langchain_core.messages import HumanMessage, SystemMessage

    try:
        return await structured_llm.ainvoke(messages)
    except Exception as first_err:
        if not is_content_filter_error(first_err):
            raise
        logger.warning("[ContentFilter] first attempt blocked (%s) — retrying with trimmed conversation",
                       _filter_categories(first_err))
        trim_note = (
            "\n\nRespond in neutral, supportive coaching tone. Keep language brief and professional."
            if language == "en"
            else "\n\nהגב בטון תומך וניטרלי. שמור על ניסוח קצר ומקצועי."
        )
        # trim the conversation only — the turn's notes travel in their own system message and must survive
        retry_messages = []
        for i, m in enumerate(messages):
            if isinstance(m, SystemMessage):
                retry_messages.append(SystemMessage(content=m.content + trim_note) if i == 0 else m)
            else:
                text = m.content if isinstance(m.content, str) else str(m.content)
                retry_messages.append(HumanMessage(content=text[-2500:]))
        if not retry_messages:
            trimmed = context[-2500:] if len(context) > 2500 else context
            retry_messages = [SystemMessage(content=system_prompt + trim_note), HumanMessage(content=trimmed)]
        try:
            return await structured_llm.ainvoke(retry_messages)
        except Exception as retry_err:
            if is_content_filter_error(retry_err):
                logger.warning("[ContentFilter] retry blocked too (%s) — user gets the fallback message",
                               _filter_categories(retry_err))
                raise ContentFilterBlockedError() from retry_err
            raise
