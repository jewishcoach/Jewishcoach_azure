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


def _coach(text, step):
    return {"sender": "coach", "content": text, "internal_state": {"current_step": step}}


def test_s9_paradigm_card_alone_does_not_skip_validation():
    state = _v3_state("S9", paradigm="ככה זה אצלי — אם אדבר זה יחמיר")
    state["messages"] = [_coach("אימות הפרדיגמה", "S9")]
    assert _check_gate_met_v3(state) is None  # the coach validates; it moves to S10 itself


def test_s9_anti_loop_moves_to_stance_not_past_it():
    state = _v3_state("S9", paradigm="ככה זה אצלי — אם אדבר זה יחמיר")
    state["messages"] = [_coach("x", "S9"), _coach("מאיזו תפיסה על החיים הוא נולד?", "S9")]
    assert _check_gate_met_v3(state) == "S10"  # one floor at a time — never straight to S11


def test_s10_stance_then_trigger_taken_from_chat_replies():
    state = _v3_state("S10", paradigm="ככה זה אצלי — אם אדבר זה יחמיר")
    state["messages"] = [
        _coach("מאיזו תפיסה על החיים הוא נולד?", "S10"),
        {"sender": "user", "content": "שהעולם מעניש את מי שמראה חולשה"},
        _coach("מאיפה זה מגיע אצלך?", "S10"),
    ]
    assert _check_gate_met_v3(state) is None
    assert state["collected_data"]["stance"]["reality_belief"] == "שהעולם מעניש את מי שמראה חולשה"
    state["messages"] += [
        {"sender": "user", "content": "מהבית, אבא שלי"},
        _coach("מה 'כפתור ההפעלה' שמדליק את התפיסה הזו?", "S10"),
        {"sender": "user", "content": "כשמרימים עליי את הקול"},
        _coach("שרשרת אחת.", "S10"),
    ]
    assert _check_gate_met_v3(state) == "S11"
    assert state["collected_data"]["stance"]["activation_trigger"] == "כשמרימים עליי את הקול"


def test_s7_waits_for_the_booklet_questions_in_chat():
    state = _v3_state("S7", gap_name="ביטול עצמי", gap_score="8")
    state["_turn_from_card"] = True
    state["messages"] = [_coach("ביטול עצמי — 8 מתוך 10. האם אתה מאמין שבפער הזה יש משהו טוב בשבילך?", "S7")]
    assert _check_gate_met_v3(state) is None  # card turn: the question was just asked
    state.pop("_turn_from_card")
    state["messages"] += [{"sender": "user", "content": "כן, הוא מראה לי מה חשוב לי"},
                          _coach("האם יש בפער הזדמנות בשבילך? אם כן — מהי?", "S7")]
    assert _check_gate_met_v3(state) is None
    state["messages"] += [{"sender": "user", "content": "להתחיל לדבר"}, _coach("שאלת הדפוס?", "S7")]
    assert _check_gate_met_v3(state) == "S8"
    assert set(state["collected_data"]["gap_booklet_moves"]) == {"belief", "opportunity"}


def test_s7_gap_card_advances_once_both_questions_answered():
    state = _v3_state("S7", gap_name="ביטול עצמי", gap_score="8", gap_booklet_moves=["belief", "opportunity"])
    assert _check_gate_met_v3(state) == "S8"


# ---------------------------------------------------------------------------
# Prompt selection
# ---------------------------------------------------------------------------

def test_s10_is_its_own_chat_stage_without_v2_precheck():
    cd = {"paradigm": "ככה זה אצלי — אם אדבר זה יחמיר"}
    prompt = assemble_system_prompt("S10", "he", ux_version=3, collected_data=cd)
    assert "S10 אמונה → עמדה → טריגר" in prompt
    assert "שלב מקדים חובה" not in prompt  # the V2 stance file's mandatory Pre-Check is not loaded


def test_s9_post_card_prompt_is_paradigm_only():
    prompt = assemble_system_prompt("S9", "he", ux_version=3, collected_data={"paradigm": "x"})
    assert "S9 פרדיגמה (קומה אחת)" in prompt


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


def test_s10_card_turn_reply_is_not_mistaken_for_stance():
    state = _v3_state("S10", paradigm="ככה זה אצלי — אם אדבר זה יחמיר")
    state["_turn_from_card"] = True
    state["messages"] = [_coach("מאיזו תפיסה על החיים הוא נולד?", "S10"),
                         {"sender": "user", "content": "[הגשת כלי]"}, _coach("...", "S10")]
    assert _check_gate_met_v3(state) is None
    assert not state["collected_data"]["stance"].get("reality_belief")


def test_closing_questions_stripped_before_card():
    from app.api.chat_v2 import strip_question_before_card
    state = {"messages": [{"sender": "coach", "content": "פתיחה.\nמה האמונה?\nאיך תנסח?"}]}
    assert strip_question_before_card(state, "פתיחה.\nמה האמונה?\nאיך תנסח?") == "פתיחה."
    assert state["messages"][-1]["content"] == "פתיחה."
    assert strip_question_before_card(state, "רק שאלה?") == "רק שאלה?"


def test_paradigm_without_rule_wording_gets_pattern_test_hint():
    from app.bsd_v2.single_agent_coach import _build_v3_paradigm_hint
    state = _v3_state("S9", paradigm="ככה זה אצלי — אם אדבר זה יחמיר")
    state["collected_data"]["paradigm"] = "ככה זה אצלי — כשמתקיפים אותי אני מתפוצץ ויוצא"
    assert "מבחן הדפוס" in _build_v3_paradigm_hint(state, "he")
    assert _build_v3_paradigm_hint(state, "he") == ""  # once only


def test_paradigm_with_rule_wording_passes():
    from app.bsd_v2.single_agent_coach import _build_v3_paradigm_hint
    state = _v3_state("S9", paradigm="ככה זה אצלי — אם אדבר זה יחמיר")
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


def test_stage_intro_falls_back_on_timeout():
    import asyncio
    from unittest.mock import patch
    import app.bsd_v2.stage_intro_generator as gen

    class SlowLLM:
        def with_structured_output(self, *a, **k):
            return self

        async def ainvoke(self, *a, **k):
            await asyncio.sleep(5)

    with patch.object(gen, "get_azure_chat_llm_4o_mini", lambda: SlowLLM()), patch.object(gen, "STAGE_INTRO_TIMEOUT_SECONDS", 0.1):
        result = asyncio.run(gen.generate_stage_intro({"collected_data": {}}, "discovery", "he"))
    assert result.stage_id == "discovery" and result.questions


def test_fix_addressee_converts_pasted_first_person_but_not_quotes():
    from app.bsd_v2.single_agent_coach import _fix_addressee
    msg = "כפי שהיית רוצה להיות עם בעלי בזמנים קשים, ומול אמא שלי. 'ככה זה אצלי — אם אדבר עם בעלי זה יחמיר'"
    out = _fix_addressee(msg, "female", "he")
    assert "להיות עם בעלך" in out and "מול אמא שלך" in out
    assert "'ככה זה אצלי — אם אדבר עם בעלי זה יחמיר'" in out  # the quoted paradigm stays verbatim
    assert _fix_addressee("בעלי חיים ובעלי הבית", "female", "he") == "בעלי חיים ובעלי הבית"


def test_fix_addressee_feminine_lets_only_for_women():
    from app.bsd_v2.single_agent_coach import _fix_addressee
    assert _fix_addressee("בוא נסכם את התמונה", "female", "he") == "בואי נסכם את התמונה"
    assert _fix_addressee("בוא נסכם את התמונה", "male", "he") == "בוא נסכם את התמונה"
    assert _fix_addressee("בוא נסכם", None, "he") == "בוא נסכם"
    assert _fix_addressee("my wife", "female", "en") == "my wife"


def test_coaching_request_composed_in_booklet_structure():
    from app.routers.tools import compose_coaching_request
    out = compose_coaching_request({"floor": "stance", "situation": "ביקורת מהבוס", "old": "העולם מעניש חולשה",
                                    "source": ["אומץ"], "nature": ["פחד מדחייה"],
                                    "new": "מותר לי להיות פגיע", "result": "אשתף את הבוס פעם אחת השבוע"})
    assert out.startswith("אני מבקש/ת להתאמן על הקושי שלי: ביקורת מהבוס")
    assert "שכאשר מופיעה העמדה הישנה שלי, שהיא העולם מעניש חולשה" in out
    assert "אפעל מתוך המקור שלי, שהוא אומץ" in out and "ומתוך הטבע שלי, שהוא פחד מדחייה" in out
    assert "ומתוך העמדה החדשה שבחרתי, שהיא מותר לי להיות פגיע" in out
    assert out.endswith("כדי שהתוצאה שאשיג תהיה: אשתף את הבוס פעם אחת השבוע.")


def test_request_card_prefills_old_and_new_floors_and_forces():
    state = _v3_state("S14", pattern="שותק ונעלם", paradigm="ככה זה אצלי — עדיף לשתוק",
                      renewal_belief="מותר לי לדבר", new_action="לומר משפט אחד אמיתי")
    state["collected_data"]["stance"]["reality_belief"] = "העולם מעניש חולשה"
    state["collected_data"]["forces"] = {"source": ["אומץ", "אמת"], "nature": ["פחד מדחייה"]}
    state["current_step"] = "S15"
    tool = resolve_post_turn_tool_call("S14", state, ux_version=3)
    assert tool["tool_type"] == "commitment_card"
    d = tool["data"]
    assert d["old"] == {"pattern": "שותק ונעלם", "paradigm": "ככה זה אצלי — עדיף לשתוק", "stance": "העולם מעניש חולשה"}
    assert d["new"]["stance"] == "מותר לי לדבר" and d["forces_source"] == ["אומץ", "אמת"]


def test_s15_prompt_is_the_request_overlay_without_v2_commitment():
    prompt = assemble_system_prompt("S15", "he", ux_version=3, collected_data={"commitment": "x"})
    assert "S15 בקשה לאימון" in prompt and "חרות" in prompt
    assert "אני מתחייב" not in prompt.split("S15 בקשה לאימון", 1)[1]


def test_s13_closes_after_declaration_even_if_coach_keeps_asking():
    state = _v3_state("S13", renewal="אני בוחרת לומר מה אני מרגישה")
    state["messages"] = [_coach("הכרה + שאלה?", "S13")]
    assert _check_gate_met_v3(state) is None  # one follow-up allowed (choice doesn't feel right yet)
    state["messages"] += [{"sender": "user", "content": "x"}, _coach("עוד שאלה?", "S13")]
    assert _check_gate_met_v3(state) == "S14"  # → stage_ready_to_complete at the macro boundary


def test_s10_belief_then_stance_position_from_chat_replies():
    state = _v3_state("S10", paradigm="ככה זה אצלי — עדיף לשתוק")
    state["collected_data"]["stance"]["reality_belief"] = "אם לא אהיה מושלמת יפסיקו לאהוב אותי"
    state["messages"] = [
        _coach("כשאת חיה מתוך האמונה הזו — איפה את עומדת מול אנשים?", "S10"),
        {"sender": "user", "content": "מרצה ומצטמצמת"},
        _coach("...", "S10"),
    ]
    assert _check_gate_met_v3(state) is None  # trigger not yet asked
    assert state["collected_data"]["stance"]["position"] == "מרצה ומצטמצמת"


def test_nature_suggestions_are_qualities_not_fears():
    from app.bsd_v2.stage_tool_triggers import _NATURE_TRAITS
    assert not any(w in t for t in _NATURE_TRAITS for w in ("פחד", "הימנעות"))


def test_pattern_motive_is_trimmed_to_the_reaction():
    from app.bsd_v2.single_agent_coach import _strip_pattern_motive
    assert _strip_pattern_motive("הדפוס שלי הוא להשתתק ולהימנע מעימותים מתוך פחד שהמצב יחמיר, גם כשאני לחוץ") \
        == "להשתתק ולהימנע מעימותים, גם כשאני לחוץ"
    assert _strip_pattern_motive("שותקת ומסתירה את הצרכים") == "שותקת ומסתירה את הצרכים"
    assert _strip_pattern_motive("מתפוצץ כי") == "מתפוצץ כי"  # too little left — keep as written


def test_s10_empty_stance_answer_gets_one_followup_not_saved():
    from app.bsd_v2.single_agent_coach import _is_empty_answer
    assert _is_empty_answer("סתם, רגיל, לא משהו.") and not _is_empty_answer("מרצה ומצטמצמת")
    state = _v3_state("S10", paradigm="ככה זה אצלי — עדיף לשתוק")
    state["collected_data"]["stance"]["reality_belief"] = "אם אדבר יחמיר"
    state["messages"] = [
        _coach("כשאתה חי מתוך האמונה הזו — איפה אתה עומד מול אנשים?", "S10"),
        {"sender": "user", "content": "סתם, רגיל, לא משהו"},
        _coach("...", "S10"),
    ]
    _check_gate_met_v3(state)
    assert not state["collected_data"]["stance"].get("position")
    state["messages"] += [
        _coach("תחזור רגע לאירוע — כשהאמונה הזו נדלקה שם, איך ראית את עצמך מול מי שהיה מולך?", "S10"),
        {"sender": "user", "content": "סתם, קטן"},
        _coach("...", "S10"),
    ]
    _check_gate_met_v3(state)
    assert state["collected_data"]["stance"]["position"] == "סתם, קטן"


def test_coach_pattern_reflection_drops_motive():
    from app.bsd_v2.single_agent_coach import _strip_motive_in_pattern_reflection
    assert _strip_motive_in_pattern_reflection(
        "הדפוס שלך — שאתה שותק מתוך פחד להיראות חלש, במקום להביע את עצמך — עכשיו נגלה מה מפעיל את הדפוס מבפנים."
    ) == "הדפוס שלך — שאתה שותק, במקום להביע את עצמך — עכשיו נגלה מה מפעיל את הדפוס מבפנים."


def test_s15_result_depending_on_others_is_detected():
    from app.bsd_v2.single_agent_coach import _result_depends_on_others
    assert _result_depends_on_others("פחות ריבים, יותר שקט בבית")
    assert _result_depends_on_others("שהבוס יעריך אותי")
    assert not _result_depends_on_others("בשבועיים הקרובים אסיים שני ויכוחים בלי לצעוק")
    assert not _result_depends_on_others("לומר את דעתי לפחות פעמיים בישיבה")


def test_s9_does_not_leave_on_a_paradigm_deepening_question():
    state = _v3_state("S9", paradigm="ככה זה אצלי — כעס זה לצעוק ולצאת")
    state["messages"] = [
        _coach("זה נשמע כמו מה שאתה עושה. איזה חוק פנימי מנחה אותך שם?", "S9"),
        {"sender": "user", "content": "ככה גדלתי"},
        _coach("כשאתה אומר 'ככה גדלתי' — איזה כלל פנימי אתה מרגיש שמנחה אותך?", "S9"),
    ]
    assert _check_gate_met_v3(state) is None
    state["messages"][-1] = _coach("החוק הזה — מאיזו תפיסה על החיים, על אנשים או על עצמך הוא נולד?", "S9")
    assert _check_gate_met_v3(state) == "S10"


def test_s10_stance_deepening_answer_replaces_belief_repeat():
    state = _v3_state("S10", paradigm="ככה זה אצלי — כעס צריך לפרוק")
    state["collected_data"]["stance"].update(reality_belief="כעס צריך לפרוק מיד", position="אני צריך לפרוק")
    state["messages"] = [
        _coach("זה החוק עצמו. ואיפה הוא שם אותך מול אנשים — איך אתה רואה את עצמך מולם?", "S10"),
        {"sender": "user", "content": "כמו מי שתמיד צריך להגן על עצמו"},
        _coach("...", "S10"),
    ]
    _check_gate_met_v3(state)
    assert state["collected_data"]["stance"]["position"] == "כמו מי שתמיד צריך להגן על עצמו"


def test_s10_root_answer_restating_the_rule_is_not_the_belief():
    from app.bsd_v2.single_agent_coach import _restates_rule
    par = "ככה זה אצלי — עדיף לשתוק מאשר להתמודד עם עימות"
    ans = "גדלתי בסביבה בלי מקום לרגשות, לכן למדתי שעדיף לשתוק כדי לשמור על השקט."
    assert _restates_rule(ans, par)
    assert not _restates_rule("שאנשים מענישים את מי שמראה חולשה", par)
    state = _v3_state("S10", paradigm=par)
    state["messages"] = [
        _coach("מה אתה יודע על העולם שגורם לחוק הזה להרגיש נכון?", "S10"),
        {"sender": "user", "content": ans},
        _coach("...", "S10"),
    ]
    _check_gate_met_v3(state)
    assert not state["collected_data"]["stance"].get("reality_belief")
    state["messages"] += [
        _coach("ומה אתה יודע על החיים או על אנשים שגורם לחוק הזה להיות נכון?", "S10"),
        {"sender": "user", "content": "שמי שמתעמת — מאבד את האנשים שלו"},
        _coach("...", "S10"),
    ]
    _check_gate_met_v3(state)
    assert state["collected_data"]["stance"]["reality_belief"] == "שמי שמתעמת — מאבד את האנשים שלו"


def test_s10_note_reads_the_reply_being_answered_now():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S10", paradigm="ככה זה אצלי — עדיף לשתוק מאשר להתמודד עם עימות")
    state["messages"] = [_coach("מה אתה יודע על העולם שגורם לחוק הזה להרגיש נכון?", "S10")]
    ctx = build_conversation_context(state, "כשהייתי ילד אבא שלי צעק, אז אנשים מענישים את מי שמדבר", "he")
    assert "כבר סיפר מאיפה זה מגיע" in ctx
    ctx = build_conversation_context(state, "גדלתי ככה, למדתי שעדיף לשתוק", "he")
    assert "חוזר על **החוק**" in ctx
