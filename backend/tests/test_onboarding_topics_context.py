"""Tests for onboarding topic hint (no heavy bsd_v2 package import)."""

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MOD_PATH = _ROOT / "app" / "bsd_v2" / "onboarding_topics_context.py"
_spec = importlib.util.spec_from_file_location("onboarding_topics_context", _MOD_PATH)
assert _spec and _spec.loader
_otc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_otc)

build_onboarding_topics_hint = _otc.build_onboarding_topics_hint
inject_onboarding_topics_into_state = _otc.inject_onboarding_topics_into_state


def test_hint_none_when_skipped():
    assert build_onboarding_topics_hint({"bsd_topics_skipped": True, "bsd_onboard_topics": ["goals"]}, "he") is None


def test_hint_hebrew_lists_topics():
    h = build_onboarding_topics_hint({"bsd_onboard_topics": ["goals", "parenting"]}, "he")
    assert h is not None
    assert "השגת יעדים" in h
    assert "הורות" in h
    assert "S2" in h


def test_hint_falls_back_single_topic_key():
    h = build_onboarding_topics_hint({"bsd_onboard_topic": "career"}, "en")
    assert h is not None
    assert "career" in h.lower()


def test_inject_removes_key_when_empty():
    state: dict = {"coach_context_onboarding_topics": "old"}
    inject_onboarding_topics_into_state(state, {}, "he")
    assert "coach_context_onboarding_topics" not in state
