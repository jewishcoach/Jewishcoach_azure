"""Unit tests for V2 station checkpoint timing and payloads."""
from datetime import datetime, timedelta, timezone

from app.bsd_v2.station_checkpoint import (
    STATION_ENTRY_STEPS,
    apply_station_intent,
    ensure_training_started_at,
    maybe_commit_station_checkpoint,
    station_time_anchor_eligible,
)
from app.bsd_v2.state_schema_v2 import create_initial_state


def _state_with_clock(**kwargs):
    st = create_initial_state("1", "1", "he")
    st.update(kwargs)
    return st


def test_station_time_requires_ten_minutes_from_start():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    started = (now - timedelta(minutes=5)).isoformat()
    s = _state_with_clock(training_started_at=started)
    assert station_time_anchor_eligible(s, now=now) is False
    started2 = (now - timedelta(minutes=11)).isoformat()
    s2 = _state_with_clock(training_started_at=started2)
    assert station_time_anchor_eligible(s2, now=now) is True


def test_station_time_resets_after_checkpoint():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    s = _state_with_clock(
        training_started_at=(now - timedelta(hours=1)).isoformat(),
        last_station_checkpoint_at=(now - timedelta(minutes=5)).isoformat(),
    )
    assert station_time_anchor_eligible(s, now=now) is False
    s2 = _state_with_clock(
        training_started_at=(now - timedelta(hours=1)).isoformat(),
        last_station_checkpoint_at=(now - timedelta(minutes=11)).isoformat(),
    )
    assert station_time_anchor_eligible(s2, now=now) is True


def test_maybe_commit_only_on_milestone_enter():
    s = _state_with_clock(
        training_started_at=(datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
    )
    assert maybe_commit_station_checkpoint(s, "S6", "S6", {"shehiya_mission_title": None, "shehiya_mission_body": None}, "he") is None
    payload = maybe_commit_station_checkpoint(
        s,
        "S6",
        "S7",
        {"shehiya_mission_title": "כותרת", "shehiya_mission_body": "גוף המשימה"},
        "he",
    )
    assert payload is not None
    assert payload["step"] == "S7"
    assert s["active_shehiya"]["title"] == "כותרת"
    # Dedupe: same step again should not emit
    assert (
        maybe_commit_station_checkpoint(
            s,
            "S7",
            "S7",
            {"shehiya_mission_title": "x", "shehiya_mission_body": "y"},
            "he",
        )
        is None
    )


def test_apply_station_intent_sets_flags():
    s = _state_with_clock()
    apply_station_intent(s, "pause_here")
    assert s["session_flow"]["paused_at_station"] is True
    apply_station_intent(s, "continue_coaching")
    assert s["session_flow"]["paused_at_station"] is False
    assert s["session_flow"]["continued_immediately_next"] is True


def test_ensure_training_started_on_first_turn():
    s = _state_with_clock(messages=[])
    ensure_training_started_at(s)
    assert "training_started_at" in s


def test_station_entry_steps_covers_s7_s15():
    assert "S7" in STATION_ENTRY_STEPS and "S15" in STATION_ENTRY_STEPS
