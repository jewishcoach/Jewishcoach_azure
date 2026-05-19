"""Fast path for onboarding intake — skip LLM on unambiguous name/gender/topic turns."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.routers.onboarding_intake import (  # noqa: E402
    OnboardingChatMessage,
    OnboardingIntakeRequest,
    _can_skip_extractor_llm,
    _deterministic_intake_response,
)


def _slots(display_name=None, gender=None, gender_skipped=False, topics=(), topics_skipped=False):
    return {
        "display_name": display_name,
        "gender": gender,
        "gender_skipped": gender_skipped,
        "topics": topics,
        "topic": topics[0] if topics else None,
        "topics_skipped": topics_skipped,
    }


def test_skip_llm_after_short_hebrew_name():
    msgs = [
        OnboardingChatMessage(role="assistant", content="איך לקרוא לך?"),
        OnboardingChatMessage(role="user", content="ישי"),
    ]
    slots = _slots(display_name="ישי")
    assert _can_skip_extractor_llm(slots, msgs, None) is True
    resp = _deterministic_intake_response(
        OnboardingIntakeRequest(language="he", messages=msgs),
        slots,
        msgs,
    )
    assert resp is not None
    assert "מגדר" in resp.assistant_message


def test_no_skip_llm_on_ambiguous_first_reply():
    msgs = [
        OnboardingChatMessage(role="assistant", content="איך לקרוא לך?"),
        OnboardingChatMessage(role="user", content="מה זה אומר בכלל?"),
    ]
    slots = _slots()
    assert _can_skip_extractor_llm(slots, msgs, None) is False
