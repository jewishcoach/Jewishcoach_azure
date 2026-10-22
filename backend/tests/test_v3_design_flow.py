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
        _coach("כשמרימים עליך את הקול. האם יש בכוחך להפעיל את הכפתור הזה, או להימנע ממנו?", "S10"),
    ]
    assert _check_gate_met_v3(state) is None  # the booklet's control question comes first (no chain)
    assert state["collected_data"]["stance"]["activation_trigger"] == "כשמרימים עליי את הקול"
    state["messages"] += [
        {"sender": "user", "content": "לא ממש, זה קורה לי"},
        _coach("זה קורה לך כמעט מעצמו. עכשיו נבדוק מה העמדה הזו נותנת לך, ומה היא לוקחת ממך.", "S10"),
    ]
    assert _check_gate_met_v3(state) == "S11"


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
    assert out.startswith("אני מבקש/ת להתאמן על הקושי להתמודד עם ביקורת מהבוס")
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
    assert _check_gate_met_v3(state) is None  # still a question open
    state["messages"] += [{"sender": "user", "content": "y"}, _coach("שאלה?", "S13"),
                          {"sender": "user", "content": "z"}, _coach("ועוד?", "S13")]
    assert _check_gate_met_v3(state) == "S14"  # cap: 4 turns → stage_ready_to_complete at the macro boundary


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


def test_s8_client_formulation_is_the_pattern_and_closes():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S8")
    state["messages"] = [
        _coach("האם אתה מכיר את עצמך מגיב ככה גם במקומות אחרים בחיים?", "S8"),
        {"sender": "user", "content": "כן, גם בעבודה"},
        _coach("ומה קורה אצלך שם — מה אתה מרגיש, מה עובר לך בראש ומה אתה עושה?", "S8"),
        {"sender": "user", "content": "מתעצבן ויוצא מהחדר"},
        _coach("כשאתה מסתכל על שני המקומות — מה חוזר אצלך? איך היית מנסח את זה במשפט אחד?", "S8"),
    ]
    ctx = build_conversation_context(state, "כעס, רצון לברוח", "he")
    assert "זה הדפוס" in ctx and "stage_ready_to_complete" in ctx
    state["messages"] += [{"sender": "user", "content": "כעס, רצון לברוח"},
                          _coach("הדפוס שלך — כעס ורצון לברוח. עכשיו נגלה מה מפעיל את הדפוס מבפנים.", "S8")]
    assert _check_gate_met_v3(state) == "S9"
    assert state["collected_data"]["pattern"] == "כעס, רצון לברוח"


def test_s8_named_field_gets_describe_one_time_not_an_assertion():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S8")
    state["messages"] = [_coach("האם אתה מכיר את עצמך מגיב ככה גם במקומות אחרים בחיים?", "S8")]
    ctx = build_conversation_context(state, "באופן כללי, גם בעבודה ועם חברים אני מוותר", "he")
    assert "פעם אחת כזו" in ctx and "אל תקבע בשבילו" in ctx
    assert "איפה למשל" in build_conversation_context(state, "כן, זה קורה גם במצבים אחרים.", "he")
    ctx = build_conversation_context(state, "בשבוע שעבר הבוס צעק עליי ושתקתי", "he")
    assert "שאלת הזיהוי והניסוח" in ctx


def test_s9_refined_rule_from_chat_replaces_the_card_paradigm():
    state = _v3_state("S9", paradigm="ככה זה אצלי — כעס, בריחה, שקט")
    state["messages"] = [
        _coach("זה מה שקורה בשטח. איזה חוק פנימי שלך אומר שזו הדרך הנכונה להגיב שם?", "S9"),
        {"sender": "user", "content": "צריך להתרחק, לא להיכנס לעימות"},
        _coach("...", "S9"),
    ]
    _check_gate_met_v3(state)
    assert state["collected_data"]["paradigm"] == "ככה זה אצלי — צריך להתרחק, לא להיכנס לעימות"


def test_s8_after_one_describe_ask_goes_to_recognition_even_if_vague():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S8")
    state["messages"] = [_coach("האם אתה מכיר את עצמך מגיב ככה גם במקומות אחרים בחיים?", "S8"),
                         {"sender": "user", "content": "גם בעבודה"},
                         _coach("ספר לי על פעם אחת כזו — מה קרה, ומה עשית?", "S8")]
    assert "שאלת הזיהוי והניסוח" in build_conversation_context(state, "סתם, כמו תמיד", "he")


def test_s7_anti_loop_ignores_turns_before_the_gap_card():
    state = _v3_state("S7")
    state["messages"] = [_coach("כרטיס הפער", "S7"), {"sender": "user", "content": "asdf"},
                         _coach("כרטיס הפער שוב", "S7"), {"sender": "user", "content": "qwer"},
                         _coach("כרטיס הפער שוב", "S7")]
    state["collected_data"].update(gap_name="כעס", gap_score=7)
    state["_turn_from_card"] = True
    state["messages"] += [{"sender": "user", "content": "[gap_card]"},
                          _coach("'כעס' — בעוצמה של 7. האם אתה מאמין שבפער הזה יש משהו טוב בשבילך?", "S7")]
    assert _check_gate_met_v3(state) is None


def test_thin_answers_get_one_different_question_then_s4_moves_on():
    from app.bsd_v2.single_agent_coach import build_conversation_context, _S4_NO_THOUGHT
    state = _v3_state("S4")
    state["messages"] = [_coach("מה האמירה הפנימית שאמרת לעצמך באותו רגע?", "S4")]
    assert "בדרך אחרת" in build_conversation_context(state, "לא משהו, סתם כעס", "he")
    state["messages"] += [{"sender": "user", "content": "לא משהו, סתם כעס"},
                          _coach("כשהיא אמרה את זה — מה עבר לך בראש? מילה או שתיים.", "S4")]
    assert "אל תשאל שוב" in build_conversation_context(state, "לא יודע, פשוט כעסתי", "he")
    state["messages"] += [{"sender": "user", "content": "לא יודע, פשוט כעסתי"},
                          _coach("זה בסדר — לא עלה משפט ברור. עכשיו נראה מה עשית בפועל באותו רגע.", "S4")]
    assert _check_gate_met_v3(state) == "S5"
    assert state["collected_data"]["thought"] == _S4_NO_THOUGHT


def test_s10_hedged_non_answer_is_not_the_belief():
    state = _v3_state("S10", paradigm="ככה זה אצלי — כעס זה לצעוק")
    state["messages"] = [_coach("מה אתה יודע על העולם שגורם לחוק הזה להרגיש נכון?", "S10"),
                         {"sender": "user", "content": "סתם, לא יודע"}, _coach("...", "S10")]
    _check_gate_met_v3(state)
    assert not state["collected_data"]["stance"].get("reality_belief")


def test_s14_one_domain_vision_gets_one_widening_question():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S14")
    state["messages"] = [_coach("איך ייראו החיים שלך כשאתה חי מתוך הבחירה הזו?", "S14")]
    assert "הרחבת החזון" in build_conversation_context(state, "פחות ריבים בבית ויותר קרבה עם אשתי", "he")
    assert "החזון עוד לא נוצר" in build_conversation_context(state, "לא משהו מיוחד", "he")
    wide = "בבית יותר קרבה, בעבודה אני מדבר בביטחון, ועם החברים אני פתוח"
    assert "הרחבת החזון" not in build_conversation_context(state, wide, "he")
    state["messages"] += [{"sender": "user", "content": "פחות ריבים בבית"},
                          _coach("זו תמונה חשובה. ואם תרים את המבט — לבית, לקשרים, לעבודה — איך נראים החיים?", "S14")]
    assert "הרחבת החזון" not in build_conversation_context(state, "עדיין בעיקר הבית", "he")


def test_s14_widening_waits_for_the_vision_question():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S14")
    state["messages"] = [_coach("הכרזת שאתה בוחר לדבר. זה מרגש.", "S13")]
    assert "הרחבת החזון" not in build_conversation_context(state, "כן, מרגיש נכון", "he")



def test_s10_note_after_trigger_asks_control_not_chain():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S10", paradigm="ככה זה אצלי — עדיף לשתוק")
    state["collected_data"]["stance"].update(reality_belief="אנשים שופטים", position="קטן ושקט")
    state["messages"] = [
        _coach("מאיפה זה מגיע אצלך?", "S10"), {"sender": "user", "content": "מהבית"},
        _coach("כשאתה חי מתוך האמונה הזו — איפה אתה עומד מול אנשים?", "S10"), {"sender": "user", "content": "קטן ושקט"},
        _coach("העמדה שלך — קטן ושקט. מה 'כפתור ההפעלה' — מה מדליק את האמונה הזו?", "S10"),
    ]
    ctx = build_conversation_context(state, "כשהבוס מרים את הקול", "he")
    assert "בכוחך להפעיל" in ctx and "בלי שרשרת" in ctx


def test_pruned_messages_keep_their_step_tag():
    from app.api.chat_v2 import _prune_state_messages
    state = {"messages": [_coach(f"m{i}", "S10") for i in range(10)]}
    _prune_state_messages(state)
    assert all((m.get("internal_state") or {}).get("current_step") == "S10" for m in state["messages"])


def test_s2_after_card_is_overlay_only_and_v3_has_no_intake_anchor():
    from app.bsd_v2.prompts.prompt_manager import assemble_system_prompt
    from app.bsd_v2.single_agent_coach import build_conversation_context
    p = assemble_system_prompt("S2", "he", "male", ux_version=3, collected_data={"event_description": "הבוס צעק"})
    assert "V3 — S2 אירוע (אחרי כרטיס האירוע)" in p and "ההודעה הראשונה ב-S2 — חובה מוחלטת" not in p
    assert "רגע ברור בזמן" not in p  # the forbidden example the model kept copying
    state = _v3_state("S3", event_description="הבוס צעק")
    state["s2_anchor"] = ["אני מרגיש: חולשה. בתחום: זוגיות"]
    assert "חולשה" not in build_conversation_context(state, "x", "he")


def test_s8_detection_edge_cases():
    from app.bsd_v2.single_agent_coach import (_describes_occurrence, _result_depends_on_others,
                                               build_conversation_context)
    assert not _describes_occurrence("גם בבית, כשאני לא מדבר על מה שמטריד אותי עם אשתי")  # "אותי" is no verb
    assert _result_depends_on_others("אבטא את הצרכים שלי פעמיים, ואקבל תגובה כנה")
    state = _v3_state("S8", event_description="ריב עם אשתי על כסף, צעקתי ויצאתי מהחדר")
    state["messages"] = [_coach("האם אתה מכיר את עצמך מגיב ככה גם במקומות אחרים בחיים?", "S8"),
                         {"sender": "user", "content": "עם אשתי בעיקר"},
                         _coach("ספר לי על פעם אחת כזו — מה קרה, ומה עשית?", "S8")]
    assert "האירוע שכבר סיפר" in build_conversation_context(state, "ריב על כסף, צעקתי ויצאתי", "he")


def test_s13_action_only_choice_gets_one_stance_question_and_answer_is_saved():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    from app.bsd_v2.stage_tool_triggers import _build_v3_tool_call
    state = _v3_state("S13", pattern="שותק", paradigm="ככה זה אצלי — עדיף לשתוק",
                      renewal_belief="אני בוחר לשמור על שקט", new_action="לנשום עמוק",
                      renewal="העמדה החדשה שבחרתי: אני בוחר לשמור על שקט. מה אעשה אחרת: לנשום עמוק")
    state["collected_data"]["stance"].update(reality_belief="אנשים שופטים", position="מרוחק, לא פתוח")
    card = _build_v3_tool_call("declaration_card", state)
    assert card["data"]["old_stance"] == "מרוחק, לא פתוח" and card["data"]["old_belief"] == "אנשים שופטים"
    state["_tool_just_submitted"] = "declaration_card"
    ctx = build_conversation_context(state, "העמדה החדשה שאני בוחר: אני בוחר לשמור על שקט", "he")
    assert "שאלת העמקה אחת לפני הסיום" in ctx and "עוד לא העמדה" in ctx
    state.pop("_tool_just_submitted")
    state["messages"] = [_coach("זה מה שתעשה. ואיך תעמוד מול אנשים מתוך הבחירה הזו — מה משתנה?", "S13"),
                         {"sender": "user", "content": "לעמוד מולם פתוח, בגובה העיניים"},
                         _coach("'לעמוד מולם פתוח, בגובה העיניים' — במקום מרוחק.", "S13")]
    assert _check_gate_met_v3(state) == "S14"
    assert state["collected_data"]["renewal_belief"] == "לעמוד מולם פתוח, בגובה העיניים"



def test_s13_holds_completion_until_stance_question_for_action_choice():
    from app.bsd_v2.single_agent_coach import _apply_v3_stage_complete_guards
    state = _v3_state("S13", renewal_belief="אשאר רגוע יותר", renewal="העמדה החדשה שבחרתי: אשאר רגוע יותר")
    state["messages"] = [_coach("'אשאר רגוע יותר' — זה מה שתעשה.", "S13")]
    internal = {"stage_ready_to_complete": True}
    _apply_v3_stage_complete_guards(state, internal)
    assert internal["stage_ready_to_complete"] is False  # the stance question was never asked
    assert _check_gate_met_v3(state) is None



def test_s13_stance_choice_also_gets_one_question_then_closes():
    state = _v3_state("S13", renewal_belief="אני בוחרת להיות פתוחה עם בן הזוג", renewal="העמדה החדשה שבחרתי: להיות פתוחה")
    state["messages"] = [_coach("'אני בוחרת להיות פתוחה עם בן הזוג' — בלי שאלה, סיום.", "S13")]
    assert _check_gate_met_v3(state) is None  # the deepening question was not asked yet
    state["messages"] = [_coach("ואיך תעמוד מול אנשים מתוך הבחירה הזו — מה משתנה במקום שאת תופסת מולם?", "S13"),
                         {"sender": "user", "content": "בגובה העיניים, לא קטנה"},
                         _coach("'בגובה העיניים, לא קטנה' — במקום להתכווץ.", "S13")]
    assert _check_gate_met_v3(state) == "S14"
    assert state["collected_data"]["renewal_belief"] == "אני בוחרת להיות פתוחה עם בן הזוג"  # no gluing
    assert state["collected_data"]["renewal_detail"] == "בגובה העיניים, לא קטנה"


def test_s13_feminine_question_counts_and_answer_gets_closing_note():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S13", renewal_belief="אני בוחרת להיות אמיצה", renewal="העמדה החדשה שבחרתי: להיות אמיצה")
    state["collected_data"]["stance"].update(position="מתכווצת וקטנה")
    state["messages"] = [_coach("ואיך תעמדי מול אנשים מתוך הבחירה הזו — מה משתנה במקום שאת תופסת מולם?", "S13")]
    ctx = build_conversation_context(state, "כשותפה, לא קטנה", "he")
    assert "סיום הבחירה" in ctx and "שאלת העמקה אחת לפני הסיום" not in ctx and "מתכווצת וקטנה" in ctx


def test_s14_is_overlay_only():
    from app.bsd_v2.prompts.prompt_manager import assemble_system_prompt
    p = assemble_system_prompt("S14", "he", "male", ux_version=3, collected_data={"renewal": "x"})
    assert "תמהיל כמ״ז" not in p and "חזון" in p


def test_arabic_lookalikes_and_feminine_note_phrases_are_fixed():
    from app.bsd_v2.single_agent_coach import _fix_addressee
    assert _fix_addressee("הכוחות לממש אותה כבר אצلك.", "female", "he") == "הכוחות לממש אותה כבר אצלך."
    out = _fix_addressee("ואם תרים את המבט — ואיך תעמוד מול אנשים?", "female", "he")
    assert "תרימי" in out and "תעמדי" in out
    assert _fix_addressee("ואם תרים את המבט", "male", "he") == "ואם תרים את המבט"


def test_confirmation_only_reply_is_not_a_stance():
    from app.bsd_v2.single_agent_coach import _thin_answer, _is_empty_answer
    assert _is_empty_answer("כן, זה מדויק. בוא נמשיך.") and _thin_answer("כן, זה מדויק. בוא נמשיך.")


def test_v3_step_never_moves_back():
    from app.bsd_v2.single_agent_coach import _block_v3_backward_step
    state = _v3_state("S11")
    internal = {"current_step": "S11"}
    _block_v3_backward_step(state, internal, old_step="S12")
    assert state["current_step"] == "S12" and internal["current_step"] == "S12"
    state = _v3_state("S13"); internal = {"current_step": "S13"}
    _block_v3_backward_step(state, internal, old_step="S12")
    assert state["current_step"] == "S13"  # forward is untouched



def test_s10_event_retold_is_not_the_stance_and_control_answer_is_not_the_trigger():
    state = _v3_state("S10", paradigm="ככה זה אצלי — עדיף לשתוק",
                      event_description="בישיבת צוות הבוס נתן קידום לקולגה ואני שתקתי וחייכתי")
    state["collected_data"]["stance"]["reality_belief"] = "ויכוחים גורמים לכאב"
    state["messages"] = [
        _coach("במילה או שתיים — כשהאמונה הזו פועלת אצלך, איך אתה רואה את עצמך מול אנשים?", "S10"),
        {"sender": "user", "content": "באותו רגע בישיבת הצוות שתקתי וחייכתי מול הבוס והקולגה"},
        _coach("...", "S10"),
    ]
    _check_gate_met_v3(state)
    assert not state["collected_data"]["stance"].get("position")
    state["collected_data"]["stance"]["activation_trigger"] = None
    state["messages"] = [
        _coach("האם יש בכוחך להפעיל את הכפתור הזה, או להימנע ממנו?", "S10"),
        {"sender": "user", "content": "אין לי שליטה, זה אוטומטי"},
        _coach("...", "S10"),
    ]
    _check_gate_met_v3(state)
    assert not state["collected_data"]["stance"].get("activation_trigger")
