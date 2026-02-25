# -*- coding: utf-8 -*-
"""
A/B Test: Gemini vs gpt-4o vs gpt-4o-mini

Deterministic assignment by conversation_id so same conversation always gets same model.
"""

import hashlib
import logging
from typing import Literal

logger = logging.getLogger(__name__)

Variant = Literal["gemini", "4o", "4o-mini"]
VARIANTS: tuple[Variant, ...] = ("gemini", "4o", "4o-mini")


def assign_variant(conversation_id: int) -> Variant:
    """
    Assign A/B variant by conversation_id (deterministic).
    ~33% each: Gemini, gpt-4o, gpt-4o-mini
    """
    h = hashlib.sha256(str(conversation_id).encode()).hexdigest()
    idx = int(h[:8], 16) % len(VARIANTS)
    return VARIANTS[idx]
