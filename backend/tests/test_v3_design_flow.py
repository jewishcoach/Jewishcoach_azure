"""
V3 flow vs. the redesign plan (docs/bsd-redesign/synthesis.md):
cards collect the data, the coach responds once and moves on, and only
asks a follow-up where the plan calls for it.
"""

from app.bsd_v2.state_schema_v2 import create_initial_state
from app.bsd_v2.single_agent_coach import _check_gate_met_v3
from app.bsd_v2.stage_tool_triggers import resolve_post_turn_tool_call
from app.bsd_v2.prompts.prompt_manager import assemble_system_prompt


def _v3_state(step: str, **cd) -> dict:
    state = create_initial_state("1", "1", "he")
    state["ux_version"] = 3
    state["current_step"] = step
    state["collected_data"].update(cd)
    return state


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------

def test_s5_waits_for_matzui_summary_confirmation():
    state = _v3_state("S5", action_actual="קמתי, לקחתי את המפתחות ויצאתי מהבית בלי מילה")
    assert _check_gate_met_v3(state) is None  # summary card shows ("האם דייקתי?")
    state["_matzui_summary_sent"] = True
    assert _check_gate_met_v3(state) == "S6"  # confirmed → desired card


def test_s5_matzui_card_shows_after_observable_action_card():
    state = _v3_state("S5", action_actual="קמתי, לקחתי את המפתחות ויצאתי מהבית בלי מילה")
    tool_call = resolve_post_turn_tool_call("S5", state, ux_version=3, from_tool_submission="action_field")
    assert tool_call and tool_call["tool_type"] == "matzui_summary"


def test_s5_interpretive_action_gets_one_grounding_turn():
    state = _v3_state("S5", action_actual="נסגרתי")
    assert _check_gate_met_v3(state) is None  # coach asks the grounding question
    assert _check_gate_met_v3(state) is None  # after the answer — summary card shows
    state["_matzui_summary_sent"] = True
    assert _check_gate_met_v3(state) == "S6"


def test_s9_card_alone_does_not_skip_validation_and_trigger():
    state = _v3_state("S9", paradigm="ככה זה אצלי — אם אדבר זה יחמיר")
    state["collected_data"]["stance"]["reality_belief"] = "העולם מעניש חולשה"
    assert _check_gate_met_v3(state) is None


def test_s9_exits_to_s11_once_trigger_answered():
    state = _v3_state("S10", paradigm="ככה זה אצלי — אם אדבר זה יחמיר")
    state["collected_data"]["stance"]["reality_belief"] = "העולם מעניש חולשה"
    state["collected_data"]["stance"]["activation_trigger"] = "כשמרימים עליי את הקול"
    assert _check_gate_met_v3(state) == "S11"


def test_s9_anti_loop_after_three_coach_turns():
    state = _v3_state("S9", paradigm="ככה זה אצלי — אם אדבר זה יחמיר")
    state["collected_data"]["stance"]["reality_belief"] = "העולם מעניש חולשה"
    state["messages"] = [
        {"sender": "coach", "content": "x", "internal_state": {"current_step": "S9"}} for _ in range(3)
    ]
    assert _check_gate_met_v3(state) == "S11"


def test_s7_gap_card_advances_immediately():
    state = _v3_state("S7", gap_name="ביטול עצמי", gap_score="8", gap_booklet_moves=["belief", "opportunity"])
    assert _check_gate_met_v3(state) == "S8"


# ---------------------------------------------------------------------------
# Prompt selection
# ---------------------------------------------------------------------------

def test_s10_does_not_load_v2_precheck():
    cd = {"paradigm": "ככה זה אצלי — אם אדבר זה יחמיר"}
    prompt = assemble_system_prompt("S10", "he", ux_version=3, collected_data=cd)
    assert "Pre-Check" in prompt  # only as the overlay's "no Pre-Check" rule
    assert "שלב מקדים חובה" not in prompt


def test_s11_pre_card_uses_pre_tool_not_post_card_overlay():
    state = _v3_state("S11")
    prompt = assemble_system_prompt("S11", "he", ux_version=3, collected_data=state["collected_data"])
    assert "V3 Card Overlay — S11" not in prompt


def test_s12_pre_card_is_short_explanation():
    state = _v3_state("S12")
    prompt = assemble_system_prompt("S12", "he", ux_version=3, collected_data=state["collected_data"])
    assert "S12 Pre-Tool" in prompt
    assert "שאלות חקירת מקור" not in prompt


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------

def test_s12_card_opens_the_stage():
    state = _v3_state("S12")
    tool_call = resolve_post_turn_tool_call("__stage_intro__", state, ux_version=3)
    assert tool_call and tool_call["tool_type"] == "trait_card_builder"


def test_s12_card_not_resent_after_submission():
    state = _v3_state("S12")
    state["trait_picker_tool_sent"] = True
    state["collected_data"]["forces"] = {"source": ["אמת"] * 6, "nature": ["פחד"] * 6}
    assert resolve_post_turn_tool_call("S12", state, ux_version=3) is None


def _s9_with_card():
    state = _v3_state("S9", paradigm="ככה זה אצלי — אם אדבר זה יחמיר")
    state["collected_data"]["stance"]["reality_belief"] = "העולם מעניש חולשה"
    return state


def test_s9_trigger_taken_from_chat_reply_to_trigger_question():
    state = _s9_with_card()
    state["messages"] = [
        {"sender": "coach", "content": "מה 'כפתור ההפעלה' שמדליק את האמונה הזו?", "internal_state": {"current_step": "S9"}},
        {"sender": "user", "content": "כשמרימים עליי את הקול"},
        {"sender": "coach", "content": "שיקוף וסיכום.", "internal_state": {"current_step": "S9"}},
    ]
    assert _check_gate_met_v3(state) == "S11"
    assert state["collected_data"]["stance"]["activation_trigger"] == "כשמרימים עליי את הקול"


def test_s9_card_submission_is_not_mistaken_for_trigger():
    state = _s9_with_card()
    state["_turn_from_card"] = True
    state["messages"] = [
        {"sender": "coach", "content": "עכשיו נגלה מה מדליק את הדפוס מבפנים?", "internal_state": {"current_step": "S9"}},
        {"sender": "user", "content": "ככה זה אצלי — ... האמונה שמאחוריו: ..."},
        {"sender": "coach", "content": "אימות + שאלת טריגר?", "internal_state": {"current_step": "S9"}},
    ]
    assert _check_gate_met_v3(state) is None


def test_closing_questions_stripped_before_card():
    from app.api.chat_v2 import strip_question_before_card
    state = {"messages": [{"sender": "coach", "content": "פתיחה.\nמה האמונה?\nאיך תנסח?"}]}
    assert strip_question_before_card(state, "פתיחה.\nמה האמונה?\nאיך תנסח?") == "פתיחה."
    assert state["messages"][-1]["content"] == "פתיחה."
    assert strip_question_before_card(state, "רק שאלה?") == "רק שאלה?"


def test_paradigm_without_rule_wording_gets_pattern_test_hint():
    from app.bsd_v2.single_agent_coach import _build_v3_paradigm_hint
    state = _s9_with_card()
    state["collected_data"]["paradigm"] = "ככה זה אצלי — כשמתקיפים אותי אני מתפוצץ ויוצא"
    assert "מבחן הדפוס" in _build_v3_paradigm_hint(state, "he")
    assert _build_v3_paradigm_hint(state, "he") == ""  # once only


def test_paradigm_with_rule_wording_passes():
    from app.bsd_v2.single_agent_coach import _build_v3_paradigm_hint
    state = _s9_with_card()
    state["collected_data"]["paradigm"] = "ככה זה אצלי — עדיף לשתוק כדי לא לעשות בלגן"
    assert _build_v3_paradigm_hint(state, "he") == ""


def test_s2_card_then_statement_moves_to_emotions():
    state = _v3_state("S2", event_description="אתמול בערב, עם אשתי — ריב על כסף, צעקתי ויצאתי")
    state["messages"] = [{"sender": "coach", "content": "עכשיו נזהה את הרגשות שעלו בך.", "internal_state": {"current_step": "S2"}}]
    assert _check_gate_met_v3(state) == "S3"
    state["messages"][-1]["content"] = "מה בדיוק נאמר שם?"
    assert _check_gate_met_v3(state) is None


def test_s14_capped_at_three_coach_turns():
    state = _v3_state("S14")
    state["messages"] = [{"sender": "coach", "content": "x", "internal_state": {"current_step": "S14"}}] * 3
    assert _check_gate_met_v3(state) == "S15"


def test_llm_cannot_leave_s5_before_matzui_card():
    import asyncio
    from unittest.mock import patch
    import app.bsd_v2.single_agent_coach as sac
    state = _v3_state("S5", emotions=["כעס"], thought="שוב זה", action_actual="קמתי ויצאתי מהבית בלי מילה")

    async def fake_llm(*a, **k):
        return "סיכום המצוי.", [], {"current_step": "S6", "saturation_score": 0.5, "collected_data": {}}

    async def passthrough(msg, internal, *a, **k):
        return msg, internal, []

    with patch.object(sac, "_call_llm_and_parse", fake_llm), patch.object(sac, "_apply_safety_nets", passthrough):
        _, out = asyncio.run(sac.handle_conversation("קמתי ויצאתי מהבית בלי מילה", state, "he"))
    assert out["current_step"] == "S5"
