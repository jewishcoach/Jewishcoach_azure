"""User chat input validation and lightweight abuse mitigation for LLM endpoints."""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Final

_CTRL_REMOVE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Rare legitimate coaching messages start with tokenizer / chat-template delimiters.
_DENY_HEAD_PREFIXES: tuple[str, ...] = (
    "[inst]",
    "<<sys>>",
    "</s>",
    "<|im_start|>system",
    "<|im_start|>assistant",
    "<|im_start|>developer",
    "[system:",
)

_XML_ROLE_AT_START = re.compile(r"(?is)^\s*<\s*(system|assistant)\s*>")


def max_chat_message_chars() -> int:
    """Upper bound for a single user message (env: CHAT_MESSAGE_MAX_CHARS, default 16000)."""
    raw = os.getenv("CHAT_MESSAGE_MAX_CHARS", "16000").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 16000
    return max(256, min(100_000, n))


MAX_CHAT_MESSAGE_CHARS: Final[int] = max_chat_message_chars()


class ChatMessageRejected(ValueError):
    """Raised when user input must not be sent to the model or stored."""

    def __init__(self, reason: str = "invalid_message"):
        self.reason = reason
        super().__init__(reason)


def _head_lower(s: str, n: int = 480) -> str:
    return s.lstrip()[:n].lower()


def looks_like_template_abuse(s: str) -> bool:
    """Conservative prefix checks for common chat-template delimiter attacks."""
    head = _head_lower(s)
    for prefix in _DENY_HEAD_PREFIXES:
        if head.startswith(prefix):
            return True
    return bool(_XML_ROLE_AT_START.match(s))


def sanitize_chat_message(raw: str) -> str:
    """
    Normalize, strip dangerous control characters, enforce max length, optional delimiter heuristics.
    Enable heuristics by default (env CHAT_PROMPT_INJECTION_HEURISTICS=false to disable).
    """
    if not isinstance(raw, str):
        raise ChatMessageRejected("invalid_type")
    s = unicodedata.normalize("NFC", raw)
    s = _CTRL_REMOVE.sub("", s)
    s = s.strip()
    if not s:
        raise ChatMessageRejected("empty")
    mx = max_chat_message_chars()
    if len(s) > mx:
        raise ChatMessageRejected("too_long")
    heuristics_on = os.getenv("CHAT_PROMPT_INJECTION_HEURISTICS", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    if heuristics_on and looks_like_template_abuse(s):
        raise ChatMessageRejected("suspicious_format")
    return s
