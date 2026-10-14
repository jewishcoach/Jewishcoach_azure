import asyncio
from unittest.mock import patch

import app.bsd_v2.safety_check as sc


def _run(message, state, assessment=None, tz=None):
    calls = []

    async def fake_classify(msg, last_coach, after_check_in):
        calls.append(after_check_in)
        return assessment

    with patch.object(sc, "_classify", fake_classify):
        return asyncio.run(sc.screen_message(message, state, tz)), calls


def test_ordinary_message_skips_classifier():
    result, calls = _run("הבוס צעק עליי בישיבה ואני שתקתי", {"messages": []})
    assert not result.intercept and calls == []


def test_idiom_classified_as_distress_continues_coaching():
    state = {"messages": []}
    result, calls = _run("בא לי למות מבושה", state, sc.RiskAssessment(level="distress"))
    assert calls == [False] and not result.intercept
    assert state["safety"].get("status") != "check_pending"


def test_possible_risk_triggers_check_in_with_israeli_lines():
    state = {"messages": []}
    result, _ = _run("לפעמים אני חושבת שעדיף שפשוט לא אהיה פה", state, sc.RiskAssessment(level="possible_risk"))
    assert result.intercept and "1201" in result.message and "101" in result.message
    assert state["safety"]["status"] == "check_pending"


def test_user_says_safe_after_check_in_resumes_coaching():
    state = {"messages": [], "safety": {"status": "check_pending"}}
    result, calls = _run("לא, אני לא אעשה כלום, אני פשוט עייפה מהכל", state,
                         sc.RiskAssessment(level="distress", user_says_safe=True))
    assert calls == [True] and not result.intercept
    assert state["safety"]["status"] == "cleared"


def test_unclear_reply_after_check_in_keeps_process_paused():
    state = {"messages": [], "safety": {"status": "check_pending"}}
    result, _ = _run("לא יודעת", state, sc.RiskAssessment(level="possible_risk"))
    assert result.intercept and "1201" in result.message
    assert state["safety"]["status"] == "check_pending"


def test_imminent_puts_emergency_first():
    state = {"messages": []}
    result, _ = _run("אני מחזיקה כדורים ביד", state, sc.RiskAssessment(level="imminent"))
    assert result.intercept and result.message.index("101") < result.message.index("1201")


def test_classifier_down_strong_wording_still_checks_in_weak_does_not():
    result, _ = _run("אני לא רוצה לחיות", {"messages": []}, None)
    assert result.intercept
    result, _ = _run("בא לי למות מבושה", {"messages": []}, None)
    assert not result.intercept


def test_help_lines_follow_time_zone():
    result, _ = _run("I want to kill myself", {"messages": []}, sc.RiskAssessment(level="possible_risk"),
                     tz="America/New_York")
    assert "988" in result.message and "911" in result.message and "1201" not in result.message
    assert sc._region("Europe/London") == "UK" and sc._region("Europe/Berlin") == "EU" and sc._region(None) == "IL"
