"""
Couple process: violence-from-the-partner screening — prefilter, check-in, release / leave quietly.
The classifier is replaced; scripts/calibrate_partner_safety.py runs the real one.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.bsd_v2 import partner_safety as ps  # noqa: E402


def _run(message, state, outputs):
    async def fake_classify(msg, last_coach, after_check_in):
        out = outputs.pop(0)
        return None if out is None else ps._PartnerOutput(**out)
    original = ps._classify
    ps._classify = fake_classify
    try:
        return asyncio.run(ps.screen_partner_message(message, state, "Asia/Jerusalem", "female"))
    finally:
        ps._classify = original


def test_ordinary_fight_never_reaches_the_classifier():
    state = {"messages": []}
    r = _run("הוא צעק עליי ויצא מהחדר, ואני בכיתי", state, [])
    assert not r.result.intercept and r.hold_action is None


def test_figurative_push_is_classified_none():
    state = {"messages": []}
    r = _run("הוא דחף אותי להחליט מהר", state, [{"level": "none"}])
    assert not r.result.intercept and r.hold_action is None


def test_violence_gets_a_private_check_in_and_holds_the_shared_screens():
    state = {"messages": []}
    r = _run("הוא הרביץ לי כשניסיתי לדבר", state, [{"level": "possible_abuse"}])
    assert r.result.intercept and r.hold_action == ps.HOLD and r.result.level == "partner_check"
    assert "118" in r.result.message and "100" in r.result.message and "את מרגישה בטוחה" in r.result.message
    assert ps.is_partner_safety_message(r.result.message)
    assert state["partner_safety"]["status"] == "check_pending"

    # she answers she's safe → released, coaching resumes
    state["messages"].append({"sender": "coach", "content": r.result.message})
    cleared = _run("זה היה ויכוח, אני מרגישה בטוחה איתו", state, [{"level": "conflict", "user_says_safe": True}])
    assert not cleared.result.intercept and cleared.hold_action == ps.RELEASE
    assert state["partner_safety"]["status"] == "cleared"


def test_check_in_not_cleared_means_going_on_alone_quietly():
    state = {"messages": [], "partner_safety": {"status": "check_pending"}}
    r = _run("אני לא יודעת", state, [{"level": "possible_abuse", "user_says_safe": False}])
    assert r.result.intercept and r.hold_action == ps.LEAVE and r.result.level == "partner_held"
    assert "לא יראו שום דבר" in r.result.message


def test_danger_gets_emergency_first():
    state = {"messages": []}
    r = _run("הוא מאיים עליי עם סכין עכשיו", state, [{"level": "danger"}])
    assert r.result.intercept and r.hold_action == ps.HOLD
    assert r.result.message.splitlines()[2].startswith("• אם יש סכנה עכשיו — משטרה: 100")


def test_classifier_down_falls_back_to_a_check_in_on_a_prefilter_hit():
    state = {"messages": []}
    r = _run("אני מפחדת ממנו", state, [None])
    assert r.result.intercept and r.hold_action == ps.HOLD
    state["messages"].append({"sender": "coach", "content": r.result.message})
    cleared = _run("אני בטוחה, הכל בסדר", state, [None])
    assert cleared.hold_action == ps.RELEASE
