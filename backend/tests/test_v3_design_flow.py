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
    state = _v3_state("S9", paradigm="ככה זה אצלי — אם אדבר זה יחמיר, אז עדיף לשתוק")
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
    assert "S10 עמדה [תפיסת המציאות]" in prompt and "איפה אתה עומד מול אנשים?" not in prompt
    assert "שלב מקדים חובה" not in prompt  # the V2 stance file's mandatory Pre-Check is not loaded


def test_s9_post_card_prompt_is_paradigm_only():
    prompt = assemble_system_prompt("S9", "he", ux_version=3, collected_data={"paradigm": "x"})
    assert "S9 פרדיגמה (קומה אחת)" in prompt


def test_s11_pre_card_uses_pre_tool_not_post_card_overlay():
    state = _v3_state("S11")
    prompt = assemble_system_prompt("S11", "he", ux_version=3, collected_data=state["collected_data"])
    assert "V3 Card Overlay — S11" not in prompt


def test_s12_opening_prompt_is_the_permission_question_only():
    state = _v3_state("S12")
    prompt = assemble_system_prompt("S12", "he", ux_version=3, collected_data=state["collected_data"], s12_phase="permission")
    assert "יש לי רשות" in prompt and "מנגנוני השמירה" in prompt and "מנגנוני ההגנה" not in prompt
    assert "שאלות חקירת מקור" not in prompt
    prompt = assemble_system_prompt("S12", "he", ux_version=3, collected_data=state["collected_data"], s12_phase="to_card")
    assert "**אסור לשאול שאלה**" in prompt and "יש לי רשות להיכנס" not in prompt


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------

def test_s12_opening_has_no_card_then_the_answer_picks_it():
    state = _v3_state("S12")
    assert resolve_post_turn_tool_call("__stage_intro__", state, ux_version=3) is None  # the permission question
    state["kamaz_permission"] = "yes"
    tool_call = resolve_post_turn_tool_call("S12", state, ux_version=3)
    assert tool_call["tool_type"] == "kamaz_discovery" and len(tool_call["data"]["questions"]) == 6
    state["kamaz_discovery_sent"] = True
    state["collected_data"]["kamaz_answers"] = [{"id": "s1", "side": "source", "text": "הקשבה"}]
    tool_call = resolve_post_turn_tool_call("S12", state, ux_version=3, from_tool_submission="kamaz_discovery")
    assert tool_call["tool_type"] == "trait_card_builder" and len(tool_call["data"]["bank"]["source"]) == 22
    declined = _v3_state("S12")
    declined["kamaz_permission"] = "no"
    tool_call = resolve_post_turn_tool_call("S12", declined, ux_version=3)
    assert tool_call["tool_type"] == "trait_card_builder" and tool_call["data"]["suggested"] == {"source": [], "nature": []}


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


def test_nature_suggestions_are_qualities_not_fears():
    from app.bsd_v2.stage_tool_triggers import _NATURE_TRAITS
    assert not any(w in t for t in _NATURE_TRAITS for w in ("פחד", "הימנעות"))


def test_pattern_motive_is_trimmed_to_the_reaction():
    from app.bsd_v2.single_agent_coach import _strip_pattern_motive
    assert _strip_pattern_motive("הדפוס שלי הוא להשתתק ולהימנע מעימותים מתוך פחד שהמצב יחמיר, גם כשאני לחוץ") \
        == "להשתתק ולהימנע מעימותים, גם כשאני לחוץ"
    assert _strip_pattern_motive("שותקת ומסתירה את הצרכים") == "שותקת ומסתירה את הצרכים"
    assert _strip_pattern_motive("מתפוצץ כי") == "מתפוצץ כי"  # too little left — keep as written


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
    assert state["collected_data"]["pattern"] == "כעס ורצון לברוח"  # the coach's clean closing reflection


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


def test_s13_holds_completion_until_stance_question_for_action_choice():
    from app.bsd_v2.single_agent_coach import _apply_v3_stage_complete_guards
    state = _v3_state("S13", renewal_belief="אשאר רגוע יותר", renewal="העמדה החדשה שבחרתי: אשאר רגוע יותר")
    state["messages"] = [_coach("'אשאר רגוע יותר' — זה מה שתעשה.", "S13")]
    internal = {"stage_ready_to_complete": True}
    _apply_v3_stage_complete_guards(state, internal)
    assert internal["stage_ready_to_complete"] is False  # the stance question was never asked
    assert _check_gate_met_v3(state) is None


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


# --- one-level stance (expert ruling Oct 22 2026; booklet p.18-19, p.29-30) ---

def test_s10_one_level_flow_origin_then_formulation_then_trigger():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S10", paradigm="ככה זה אצלי — עדיף לשתוק",
                      event_description="בישיבת צוות הבוס נתן קידום לקולגה ואני שתקתי וחייכתי")
    state["messages"] = [_coach("מה אתה יודע על העולם שגורם לחוק הזה להרגיש נכון?", "S10")]
    ctx = build_conversation_context(state, "שוויכוחים מרחיקים אנשים", "he")
    assert "שאלת המקור" in ctx and "איפה אתה עומד" not in ctx
    state["messages"] += [{"sender": "user", "content": "שוויכוחים מרחיקים אנשים"},
                          _coach("מאיפה זה מגיע אצלך? יש מקום, תקופה או אדם שממנו למדת שככה זה?", "S10")]
    ctx = build_conversation_context(state, "בילדות, כשהוריי רבו", "he")
    assert "לנסח את העמדה בעצמו" in ctx
    state["messages"] += [{"sender": "user", "content": "בילדות, כשהוריי רבו"},
                          _coach("ואם תנסח את העמדה שלך במשפט אחד — 'אני מאמין ש…' — מה המשפט?", "S10"),
                          {"sender": "user", "content": "אני מאמין שוויכוחים גורמים לכאב ולמרחק"},
                          _coach("...", "S10")]
    _check_gate_met_v3(state)
    assert state["collected_data"]["stance"]["reality_belief"] == "אני מאמין שוויכוחים גורמים לכאב ולמרחק"
    state["messages"].pop()
    ctx = build_conversation_context(state, "אני מאמין שוויכוחים גורמים לכאב ולמרחק", "he")
    assert "שאלת טריגר אחת" in ctx and "stance.short" in ctx


def test_s10_event_retold_is_not_the_stance_and_control_answer_is_not_the_trigger():
    state = _v3_state("S10", paradigm="ככה זה אצלי — עדיף לשתוק",
                      event_description="בישיבת צוות הבוס נתן קידום לקולגה ואני שתקתי וחייכתי")
    state["collected_data"]["stance"]["reality_belief"] = "ויכוחים גורמים לכאב"
    state["messages"] = [
        _coach("ואם תנסח את העמדה שלך במשפט אחד — 'אני מאמין ש…' — מה המשפט?", "S10"),
        {"sender": "user", "content": "באותו רגע בישיבת הצוות שתקתי וחייכתי מול הבוס והקולגה"},
        _coach("...", "S10"),
    ]
    _check_gate_met_v3(state)
    assert state["collected_data"]["stance"]["reality_belief"] == "ויכוחים גורמים לכאב"
    state["messages"] = [
        _coach("האם יש בכוחך להפעיל את הכפתור הזה, או להימנע ממנו?", "S10"),
        {"sender": "user", "content": "אין לי שליטה, זה אוטומטי"},
        _coach("...", "S10"),
    ]
    _check_gate_met_v3(state)
    assert not state["collected_data"]["stance"].get("activation_trigger")


def test_s13_action_only_choice_gets_one_perception_question_and_answer_replaces_it():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    from app.bsd_v2.stage_tool_triggers import _build_v3_tool_call
    state = _v3_state("S13", pattern="שותק", paradigm="ככה זה אצלי — עדיף לשתוק",
                      renewal_belief="אני בוחר לשמור על שקט", new_action="לנשום עמוק",
                      renewal="העמדה החדשה שבחרתי: אני בוחר לשמור על שקט. מה אעשה אחרת: לנשום עמוק")
    state["collected_data"]["stance"].update(reality_belief="אני מאמין שוויכוחים מרחיקים",
                                             short="אני מאמין שוויכוחים מרחיקים")
    card = _build_v3_tool_call("declaration_card", state)
    assert card["data"]["old_stance"] == "אני מאמין שוויכוחים מרחיקים"
    state["_tool_just_submitted"] = "declaration_card"
    ctx = build_conversation_context(state, "העמדה החדשה שאני בוחר: אני בוחר לשמור על שקט", "he")
    assert "ומה אתה מאמין מעכשיו" in ctx and "איך תעמוד מול אנשים" not in ctx
    state.pop("_tool_just_submitted")
    state["messages"] = [_coach("זה מה שתעשה. ומה אתה מאמין מעכשיו — איך היית מנסח את העמדה החדשה: 'אני מאמין ש…'?", "S13"),
                         {"sender": "user", "content": "אני מאמין שלקול שלי יש ערך"},
                         _coach("'אני מאמין שלקול שלי יש ערך' — במקום שוויכוחים מרחיקים.", "S13")]
    assert _check_gate_met_v3(state) == "S14"
    assert state["collected_data"]["renewal_belief"] == "אני מאמין שלקול שלי יש ערך"  # replaced, not glued


def test_s13_perception_choice_closes_without_a_question():
    from app.bsd_v2.single_agent_coach import build_conversation_context, _s13_stance_question_pending
    state = _v3_state("S13", renewal_belief="אני מאמין שלקול שלי יש ערך", renewal="העמדה החדשה שבחרתי: אני מאמין שלקול שלי יש ערך")
    assert not _s13_stance_question_pending(state)
    state["_tool_just_submitted"] = "declaration_card"
    assert "שאלת העמקה אחת לפני הסיום" not in build_conversation_context(state, "x", "he")


def test_coaching_request_quotes_first_person_stances():
    from app.routers.tools import compose_coaching_request
    out = compose_coaching_request({"floor": "stance", "situation": "ישיבות צוות", "old": "אני מאמין שוויכוחים מרחיקים.",
                                    "new": "אני מאמין שלקול שלי יש ערך", "result": "אביע דעה פעם אחת"})
    assert 'שהיא "אני מאמין שוויכוחים מרחיקים"' in out and 'שהיא "אני מאמין שלקול שלי יש ערך"' in out


def test_s15_result_answer_updates_only_the_result_and_request_is_recomposed():
    req = {"floor": "stance", "situation": "כעס מול הבן", "old": "אני מאמין שבלי סמכות המשפחה תתפרק",
           "source": ["אהבה"], "nature": ["זהירות"], "new": "אני מאמין שקרבה מחזקת", "result": "פחות צעקות"}
    state = _v3_state("S15", coaching_request=dict(req), commitment="טקסט שהמודל כתב במקום הבקשה")
    state["messages"] = [_coach("מה מתוך זה תלוי בך — מה אתה תעשה, או איך תהיה, שאפשר יהיה לראות?", "S15"),
                         {"sender": "user", "content": "אעצור לפני שאני צועק ואקשיב"},
                         _coach("...", "S15")]
    _check_gate_met_v3(state)
    commitment = state["collected_data"]["commitment"]
    assert commitment.startswith("אני מבקש/ת להתאמן על הקושי להתמודד עם כעס מול הבן")
    assert commitment.endswith("כדי שהתוצאה שאשיג תהיה: אעצור לפני שאני צועק ואקשיב.")


def test_coaching_request_situation_and_leading_yes():
    from app.bsd_v2.coaching_request import compose_coaching_request
    out = compose_coaching_request({"floor": "pattern", "situation": "כשאני במפגש צוות", "old": "כן, אני שותק",
                                    "new": "אדבר", "result": "x"})
    assert "להתמודד עם הרגעים שאני במפגש צוות" in out and 'שהוא "אני שותק"' in out


def test_control_character_artifacts_are_removed():
    from app.bsd_v2.single_agent_coach import _sanitize_coach_message
    assert _sanitize_coach_message("מה ה\x173אמירה הפנימית\x187 שאמרת") == "מה האמירה הפנימית שאמרת"
    assert _sanitize_coach_message("פער של 7 מתוך 10") == "פער של 7 מתוך 10"


def test_s10_cap_counts_the_whole_step_and_deepening_is_asked_once():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S10", paradigm="ככה זה אצלי — אני מעדיף לשמור על השקט")
    state["messages"] = []
    for i in range(7):
        state["messages"] += [_coach(f"שאלה {i}?", "S10"), {"sender": "user", "content": f"תשובה {i}"}]
    state["messages"].append(_coach("...", "S10"))
    assert _check_gate_met_v3(state) == "S11"  # 8 S10 turns — the cap now fires
    state = _v3_state("S10", paradigm="ככה זה אצלי — אני מעדיף לשמור על השקט")
    state["messages"] = [_coach("מה אתה יודע על החיים שגורם לחוק הזה להרגיש נכון?", "S10"),
                         {"sender": "user", "content": "למדתי שעדיף לשמור על השקט"},
                         _coach("ומה אתה יודע על אנשים שגורם לתגובה הזו להרגיש נכונה?", "S10")]
    ctx = build_conversation_context(state, "שאנשים לא באמת מקשיבים", "he")
    assert "שמעמיקה מתחת לחוק" not in ctx  # the deepening (in other words) was already asked


def test_s8_asks_for_another_arena_and_stores_the_clean_pattern():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S8", event_description="בישיבת צוות הבוס קידם קולגה צעיר ואני שתקתי")
    state["messages"] = [_coach("האם אתה מכיר את עצמך מגיב ככה גם במקומות אחרים בחיים?", "S8")]
    ctx = build_conversation_context(state, "כן, גם בבית מול אשתי וגם בעבודה בישיבות", "he")
    assert "מזירה אחרת" in ctx and "פעם אחת כזו בבית" in ctx
    state["messages"] += [{"sender": "user", "content": "אני נמנע מלהביע כי אני מפחד, ולכן שותק גם בעבודה וגם בבית"},
                          _coach("הדפוס שלך — להימנע מלהביע את מה שאתה מרגיש ולשמור על שתיקה גם בעבודה וגם בבית. "
                                 "עכשיו נגלה מה מפעיל את הדפוס מבפנים.", "S8")]
    state["messages"].insert(1, {"sender": "user", "content": "x"})
    state["messages"].insert(2, _coach("כשאתה מסתכל על שני הרגעים — האם אתה מזהה כאן משהו שחוזר על עצמו? איך היית מנסח אותו במשפט אחד?", "S8"))
    assert _check_gate_met_v3(state) == "S9"
    assert state["collected_data"]["pattern"] == "להימנע מלהביע את מה שאתה מרגיש ולשמור על שתיקה"


def test_coaching_request_is_always_on_the_stance_floor_and_reads_with_a_verb_situation():
    from app.bsd_v2.coaching_request import compose_coaching_request
    out = compose_coaching_request({"situation": "לדבר על מה שמפריע לי בעבודה", "old": "אני מאמין שלהראות רגשות זה סיכון",
                                    "new": "אני מאמין שפתיחות מקרבת", "result": "אדבר פעם בשבוע"})
    assert out.startswith("אני מבקש/ת להתאמן על הקושי שלי לדבר על מה שמפריע לי בעבודה")
    assert "שכאשר מופיעה העמדה הישנה שלי" in out and "ומתוך העמדה החדשה שבחרתי" in out


def test_s10_rule_like_formulation_gets_one_deepening_and_is_not_the_stance():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S10", paradigm="ככה זה אצלי — עדיף לשתוק")
    state["collected_data"]["stance"]["reality_belief"] = "ויכוחים מרחיקים"
    state["messages"] = [
        _coach("מה אתה יודע על העולם שגורם לחוק הזה להרגיש נכון?", "S10"), {"sender": "user", "content": "ויכוחים מרחיקים"},
        _coach("מאיפה זה מגיע אצלך?", "S10"), {"sender": "user", "content": "בילדות, כשהוריי רבו"},
        _coach("ואם תנסח את העמדה שלך במשפט אחד — 'אני מאמין ש…' — מה המשפט?", "S10"),
    ]
    ctx = build_conversation_context(state, "אני מאמין שעדיף לשתוק ולשמור על השקט", "he")
    assert "עדיין **חוק**" in ctx
    state["messages"] += [{"sender": "user", "content": "אני מאמין שעדיף לשתוק ולשמור על השקט"}, _coach("...", "S10")]
    _check_gate_met_v3(state)
    assert state["collected_data"]["stance"]["reality_belief"] == "ויכוחים מרחיקים"  # the rule was not saved


def test_vision_is_never_kept_before_s14_asked_for_it():
    from app.bsd_v2.single_agent_coach import _drop_premature_vision
    state = _v3_state("S14", vision="אני מאמין שקרבה מחזקת")  # the model copied the new stance at S13
    _drop_premature_vision(state, old_step="S13")
    assert "vision" not in state["collected_data"]
    state["collected_data"]["vision"] = "בית שקט, עבודה שאני משפיע בה"
    _drop_premature_vision(state, old_step="S14")  # a real S14 answer stays
    assert state["collected_data"]["vision"] == "בית שקט, עבודה שאני משפיע בה"


def test_coaching_request_accepts_a_string_force():
    from app.bsd_v2.coaching_request import compose_coaching_request
    out = compose_coaching_request({"situation": "x", "old": "y", "source": "אומץ", "nature": "צורך בביטחון", "new": "z", "result": "w"})
    assert "שהוא אומץ" in out and "שהוא צורך בביטחון" in out and "צ, ו" not in out


def test_s8_reflection_net_drops_motive_arenas_and_premature_pattern():
    from app.bsd_v2.single_agent_coach import _strip_motive_in_pattern_reflection as f
    assert f("הדפוס שלך הוא לבחור לשתוק מתוך חשש מהקונפליקט, גם כשזה כואב. עכשיו נגלה.") == \
        "הדפוס שלך הוא לבחור לשתוק, גם כשזה כואב. עכשיו נגלה."
    assert "גם בעבודה" not in f("הדפוס שלך — לשתוק ולהתמודד לבד, גם בעבודה וגם בזוגיות. עכשיו נגלה.")
    assert "הדפוס שלך" not in f("הדפוס שלך — לשתוק. כשאתה מסתכל על שני הרגעים, מה חוזר?", formulated=False)


def test_s15_result_issues():
    from app.bsd_v2.single_agent_coach import _result_issue
    assert _result_issue("אדבר פעם בשבוע עם האישה והבוס") == "two_arenas"
    assert _result_issue("בשבת הבאה אנסה לדבר בשקט") == "hedge"
    assert _result_issue("שהבוס יעריך אותי") == "others"
    assert _result_issue("אדבר בישיבת הצוות הבאה פעם אחת") == ""


def test_coaching_request_no_doubled_difficulty():
    from app.bsd_v2.coaching_request import compose_coaching_request
    out = compose_coaching_request({"situation": "קושי לבטא את הצרכים מול בן הזוג", "old": "x", "new": "y", "result": "z"})
    assert out.startswith("אני מבקש/ת להתאמן על הקושי שלי לבטא את הצרכים מול בן הזוג")


def test_pattern_drops_its_emotional_result():
    from app.bsd_v2.single_agent_coach import _strip_pattern_motive
    assert _strip_pattern_motive("להשתיק את עצמך ולוותר על הצרכים שלך, וזה גורם לך להרגיש קטנה ומתוסכלת") == \
        "להשתיק את עצמך ולוותר על הצרכים שלך"


def test_stage_complete_field_does_not_suggest_floor_closing_wording():
    from app.bsd_v2.response_schema import InternalStateSchema
    desc = InternalStateSchema.model_fields["stage_ready_to_complete"].description
    assert "לסגור" not in desc and "לסכם" not in desc


def test_feminine_stance_sentences():
    from app.bsd_v2.single_agent_coach import _feminize_stances, _fix_addressee
    cd = {"stance": {"reality_belief": "אני מאמין שצריך להראות חוזק", "short": "אני מאמין שצריך חוזק"},
          "renewal_belief": "אני מאמין שפתיחות מחזקת"}
    _feminize_stances(cd)
    assert cd["stance"]["short"] == "אני מאמינה שצריך חוזק" and cd["renewal_belief"].startswith("אני מאמינה ש")
    assert "'אני מאמינה ש" in _fix_addressee("העמדה שלך — 'אני מאמין שצריך חוזק'.", "female", "he")


def test_pattern_drops_leading_fear_cause_and_feeling():
    from app.bsd_v2.single_agent_coach import _strip_pattern_motive
    assert _strip_pattern_motive("אני מפחדת להביע את עצמי, ולכן אני שותקת ומרגישה קטנה ומתוסכלת") == "אני שותקת"
    assert _strip_pattern_motive("אני נמנע מלהביע את האמת שלי, ולכן נשאר שקט") == "אני נמנע מלהביע את האמת שלי, ולכן נשאר שקט"


def test_s10_non_answer_to_an_early_trigger_is_not_the_trigger_and_it_is_asked_again():
    # Michal's run: the trigger asked before the origin, met with "בוא נמשיך"; after the formulation the note said
    # "the last answer is the trigger" and the cap closed S10 on an unanswered trigger question
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S10", paradigm="ככה זה אצלי — אני חוששת שאם אבקש יחשבו שאני מעמיסה")
    state["messages"] = [_coach("מה 'כפתור ההפעלה' — מה קורה במציאות שמדליק את העמדה הזו?", "S10"),
                         {"sender": "user", "content": "כן, זה מדויק. בוא נמשיך."},
                         _coach("מאיפה זה מגיע אצלך?", "S10")]
    _check_gate_met_v3(state)
    assert not state["collected_data"]["stance"].get("activation_trigger")
    state["messages"] += [{"sender": "user", "content": "מהילדות, כשההורים כעסו כשביקשתי"},
                          _coach("ואם תנסחי את העמדה שלך במשפט אחד — 'אני מאמינה ש…' — מה המשפט?", "S10")]
    ctx = build_conversation_context(state, "אני מאמינה שאם אבקש יותר מדי, אנשים יתרחקו ממני", "he")
    assert "שאלת טריגר אחת" in ctx and "בכוחך להפעיל" not in ctx


def test_s10_last_turn_before_the_cap_closes_without_a_question():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S10", paradigm="ככה זה אצלי — אני מעדיף לשמור על השקט")
    state["messages"] = []
    for i in range(6):
        state["messages"] += [_coach(f"שאלה {i}?", "S10"), {"sender": "user", "content": f"תשובה {i}"}]
    state["messages"].pop()
    ctx = build_conversation_context(state, "תשובה 5", "he")
    assert "התור האחרון בעמדה" in ctx and "**בלי שאלה**" in ctx


def test_s10_desired_belief_as_formulation_gets_one_question_about_today():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S10", paradigm="ככה זה אצלי — אני חוששת שאם אגיד מה אני מרגישה תהיה מריבה, אז עדיף לשתוק")
    state["messages"] = [_coach("מה את יודעת על החיים שגורם לחוק הזה להרגיש נכון?", "S10"),
                         {"sender": "user", "content": "גדלתי בבית שבו כשדיברתי זה רק יצר בעיות"},
                         _coach("ואם תנסחי את העמדה שלך במשפט אחד — 'אני מאמינה ש…' — מה המשפט?", "S10")]
    desired = "אני מאמינה שאפשר לשמור על הקשר גם כשאני מבטאת את הצרכים שלי"
    ctx = build_conversation_context(state, desired, "he")
    assert "רוצה** להאמין" in ctx and "שאלת טריגר אחת" not in ctx
    state["messages"] += [{"sender": "user", "content": desired},
                          _coach("זה נשמע כמו מה שהיית רוצה להאמין. ומה את מאמינה היום — מה המשפט?", "S10")]
    ctx = build_conversation_context(state, "אני מאמינה שאם אדבר, יכעסו עליי ויעזבו", "he")
    assert "שאלת טריגר אחת" in ctx  # asked once; the answer to it is the stance


def test_pattern_cut_leaves_no_dangling_connector():
    from app.bsd_v2.single_agent_coach import _strip_pattern_motive as f
    assert f("אני שקטה, לא מבטאת את הצרכים שלי כדי לא ליצור קונפליקט, אבל בסוף זה גורם לי להרגיש מותשת") == \
        "אני שקטה, לא מבטאת את הצרכים שלי"
    assert f("אני שותק כדי לא לריב, ואז מתפוצץ") == "אני שותק, ואז מתפוצץ"


def test_stance_keeps_the_perception_and_drops_the_rule_tail():
    from app.bsd_v2.single_agent_coach import _clean_stances, _stance_is_a_rule
    said = "אני מאמינה שכשאני מבקשת משהו, אנשים מתרחקים ממני, ולכן עדיף לי לשתוק כדי לשמור על הקשר"
    assert not _stance_is_a_rule(said) and _stance_is_a_rule("אני מאמין שעדיף לשתוק ולשמור על השקט")
    cd = {"stance": {"reality_belief": said, "short": "כשאני מבקשת משהו, אנשים מתרחקים ממני ולכן עדיף לי לשתוק"}}
    _clean_stances(cd)
    assert cd["stance"]["reality_belief"] == "אני מאמינה שכשאני מבקשת משהו, אנשים מתרחקים ממני"
    assert cd["stance"]["short"] == "אני מאמין שכשאני מבקשת משהו, אנשים מתרחקים ממני"  # feminized after, per gender


def test_other_arena_time_is_not_the_event_on_common_words():
    from app.bsd_v2.single_agent_coach import _same_as_event
    event = "הזמנתי ארוחת ערב רומנטית והוא ביטל כי חבר הזמין אותו לכדורגל. אמרתי 'בסדר' וסידרתי לבד את השולחן."
    assert not _same_as_event("בפגישה בעבודה מישהו קטע אותי. לא אמרתי כלום, פשוט התכווצתי במקום להסביר למה הרעיון שלי חשוב", event)
    assert _same_as_event("כשהוא ביטל את ארוחת הערב בשביל הכדורגל", event)


def test_s8_confirmation_uses_the_infinitive_and_drops_cause_and_feeling():
    from app.bsd_v2.single_agent_coach import _strip_motive_in_pattern_reflection as f
    out = f("הדפוס שלך — לשתוק ולוותר על הצרכים שלך מתוך פחד לאבד אותו, וזה גורם לך להרגיש לבד. עכשיו נגלה מה מפעיל את הדפוס מבפנים.")
    assert out == "הדפוס שלך הוא לשתוק ולוותר על הצרכים שלך. עכשיו נגלה מה מפעיל את הדפוס מבפנים."
    state = _v3_state("S8", event_description="בערב הוא ביטל את הארוחה ואמרתי בסדר")
    state["messages"] = [_coach("כשאת מסתכלת על שני הרגעים — האם את מזהה כאן משהו שחוזר על עצמו? איך היית מנסחת אותו במשפט אחד?", "S8"),
                         {"sender": "user", "content": "אני נמנעת מלבטא את הצרכים שלי"},
                         _coach("הדפוס שלך הוא להימנע מלבטא את הצרכים שלך. עכשיו נגלה מה מפעיל את הדפוס מבפנים.", "S8")]
    assert _check_gate_met_v3(state) == "S9"
    assert state["collected_data"]["pattern"] == "להימנע מלבטא את הצרכים שלך"


def test_s9_fear_only_paradigm_asks_for_the_action_rule_and_joins_the_answer():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    fear = "ככה זה אצלי — אני חושבת שאם אבקש עזרה, ידחו אותי"
    state = _v3_state("S9", paradigm=fear)
    state["_tool_just_submitted"] = "sentence_builder"
    state["messages"] = [_coach("זיהינו את הדפוס שלך — לשתוק. בכרטיס שמופיע מתחת — נשים לו מילים.", "S9")]
    ctx = build_conversation_context(state, fear, "he")
    assert "חוק הפעולה" in ctx and "שאלת השורש" not in ctx
    state.pop("_tool_just_submitted")
    state["messages"] += [{"sender": "user", "content": fear},
                          _coach("זהו החשש שלך. ומהו חוק הפעולה הפנימי שאומר לך איך נכון להגיב במצב כזה?", "S9")]
    assert _check_gate_met_v3(state) is None  # not before the question was asked and answered
    state["messages"] += [{"sender": "user", "content": "לכן עדיף לשתוק"},
                          _coach("החוק הזה — מאיזו תפיסה על החיים הוא נולד? מה את יודעת על העולם שגורם לו להרגיש נכון?", "S10")]
    _check_gate_met_v3(state)
    assert state["collected_data"]["paradigm"] == "ככה זה אצלי — אני חושבת שאם אבקש עזרה, ידחו אותי, לכן עדיף לשתוק"


def test_s9_paradigm_with_an_action_rule_is_accepted():
    from app.bsd_v2.single_agent_coach import _s9_fear_only
    state = _v3_state("S9", paradigm="ככה זה אצלי — אם אבקש עזרה ידחו אותי, אז עדיף להסתדר לבד")
    state["messages"] = []
    assert not _s9_fear_only(state)


def test_proofread_keeps_only_light_edits():
    from app.bsd_v2.proofread import _acceptable
    src = "אני מאמינה שאם אדבר, אנשים יתרחקו ויישארו לי לבד"
    assert _acceptable(src, "אני מאמינה שאם אדבר, אנשים יתרחקו ואשאר לבד")
    assert not _acceptable("אני מאמין שאם לא אשתוק, לא יאהבו אותי", "אני מאמין שאם אשתוק, יאהבו אותי")  # polarity
    assert not _acceptable(src, "אני מאמינה שדיבור מרחיק אנשים")  # rewritten


def test_pattern_head_infinitive_is_repaired_and_not_inside_a_sentence():
    from app.bsd_v2.single_agent_coach import _fix_pattern_infinitive as g, _strip_motive_in_pattern_reflection as f
    assert g("לנמנע מלהביע את עצמך") == "להימנע מלהביע את עצמך" and g("למתכווץ פנימה") == "להתכווץ פנימה"
    assert g("לנסות לרצות את כולם") == "לנסות לרצות את כולם" and g("לנהל הכול לבד") == "לנהל הכול לבד"
    assert f("זיהינו את הדפוס שלך — להימנע. מתחת לדפוס יש חוק פנימי.") == "זיהינו את הדפוס שלך — להימנע. מתחת לדפוס יש חוק פנימי."


def test_short_stance_cut_inside_the_condition_falls_back_to_the_whole_sentence():
    from app.bsd_v2.single_agent_coach import _clean_stances
    belief = "אני מאמינה שאם אדרוש יותר מדי, אנשים יראו אותי כחסרת ערך"
    cd = {"stance": {"reality_belief": belief, "short": "אני מאמינה שאם אדרוש יותר מדי."}}
    _clean_stances(cd)
    assert cd["stance"]["short"] == belief
    cd = {"stance": {"reality_belief": "אני מאמינה שכשאני מבקשת, אנשים מתרחקים ממני ולא חוזרים", "short": "אני מאמינה שכשאני מבקשת, אנשים מתרחקים ממני"}}
    _clean_stances(cd)
    assert cd["stance"]["short"] == "אני מאמינה שכשאני מבקשת, אנשים מתרחקים ממני"  # a complete shortening stays


def test_general_claim_with_a_ti_noun_is_not_a_described_time():
    from app.bsd_v2.single_agent_coach import _describes_occurrence
    assert not _describes_occurrence("כן, גם בעבודה לפעמים אני נמנעת מלהביע את דעתי או לבקש עזרה")
    assert _describes_occurrence("ביקשתי עזרה בפרויקט ושתקתי כשסירבו")


def test_s9_refined_rule_is_stored_when_the_coach_moves_to_s10_in_the_same_turn():
    state = _v3_state("S10", paradigm="ככה זה אצלי — כשאני מרגישה לא מוערכת, אני שותקת")
    state["messages"] = [_coach("המשפט מתאר את התגובה. איזה חוק פנימי שלך אומר שזו הדרך הנכונה להגיב?", "S9"),
                         {"sender": "user", "content": "החוק הפנימי שלי הוא שאם אדבר זה יגרום לסכסוך, ולכן עדיף לשתוק"},
                         _coach("החוק הזה — מאיזו תפיסה על החיים הוא נולד?", "S10")]
    _check_gate_met_v3(state)
    assert state["collected_data"]["paradigm"] == "ככה זה אצלי — אם אדבר זה יגרום לסכסוך, ולכן עדיף לשתוק"


def test_request_situation_keeps_the_when_clause_only():
    from app.bsd_v2.coaching_request import _difficulty
    assert _difficulty("כשאני מרגישה לא מוערכת בבית, אני נשארת לבד עם הכאב שלי.") == \
        "הקושי להתמודד עם הרגעים שאני מרגישה לא מוערכת בבית"


def test_s9_pattern_hint_does_not_fire_on_a_fear_paradigm_after_the_action_question():
    from app.bsd_v2.single_agent_coach import _build_v3_paradigm_hint
    state = _v3_state("S9", paradigm="ככה זה אצלי — אני חושבת שאם אגיד מה אני מרגישה, אני אכשל")
    state["messages"] = [_coach("זהו החשש שלך. ומהו חוק הפעולה הפנימי שאומר לך איך נכון להגיב במצב כזה?", "S9")]
    assert _build_v3_paradigm_hint(state, "he") == ""


def test_long_short_stance_takes_the_i_believe_sentence():
    from app.bsd_v2.single_agent_coach import _clean_stances
    b = ("אני חושבת שהעולם הוא מקום לא בטוח, שאם אני לא שקטה, אנשים יפסיקו לאהוב אותי או יפגעו בי בכל מקום. "
         "אני מאמינה שאהבה תלויה בהתנהגות שלי, ולא בזכותי להיות מי שאני")
    cd = {"stance": {"reality_belief": b, "short": b}}
    _clean_stances(cd)
    assert cd["stance"]["short"] == "אני מאמינה שאהבה תלויה בהתנהגות שלי, ולא בזכותי להיות מי שאני"


def test_s10_stance_formulated_in_the_root_answer_is_taken_without_another_deepening():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S10", paradigm="ככה זה אצלי — עדיף לשתוק ולהימנע מעימות")
    answer = "אני מאמינה שאם אגיד את מה שאני מרגישה, זה יהרוס את הקשר, ולכן עדיף לשמור על השקט"
    state["messages"] = [_coach("החוק הזה — מאיזו תפיסה על החיים הוא נולד? מה את יודעת על העולם שגורם לו להרגיש נכון?", "S10"),
                         {"sender": "user", "content": answer}, _coach("...", "S10")]
    _check_gate_met_v3(state)
    assert state["collected_data"]["stance"]["reality_belief"] == "אני מאמינה שאם אגיד את מה שאני מרגישה, זה יהרוס את הקשר"
    state["messages"].pop()
    ctx = build_conversation_context(state, answer, "he")
    assert "שאלת המקור" in ctx and "שמעמיקה מתחת לחוק" not in ctx


def test_result_depending_on_the_partner_in_present_tense():
    from app.bsd_v2.single_agent_coach import _result_issue
    assert _result_issue("אדבר איתו פעם בשבוע ומרגישה שהוא מקשיב ומכבד אותי") == "others"
    assert _result_issue("כשהוא מבקש ממני, אגיד לו מה אני מרגישה") == ""


def test_turn_notes_travel_in_a_system_message_and_survive_the_filter_retry():
    import asyncio
    from langchain_core.messages import HumanMessage, SystemMessage
    from app.bsd_v2.single_agent_coach import _coach_messages, build_conversation_context
    from app.azure_openai_content_filter import invoke_structured_coach_llm
    state = _v3_state("S10", paradigm="ככה זה אצלי — עדיף לשתוק")
    state["messages"] = [_coach("מאיפה זה מגיע אצלך?", "S10"), {"sender": "user", "content": "מהבית"}]
    ctx = build_conversation_context(state, "מהילדות", "he")
    msgs = _coach_messages("SYSTEM", ctx, "\n**בדיקת מערכת (S9):** x")
    assert [type(m) for m in msgs] == [SystemMessage, SystemMessage, HumanMessage]
    assert "שלב נעול" in msgs[1].content and "בדיקת מערכת" in msgs[1].content
    assert "שלב נעול" not in msgs[2].content and msgs[2].content.endswith("משתמש: מהילדות")

    class FilterOnce:
        def __init__(self): self.calls = []
        async def ainvoke(self, m):
            self.calls.append(m)
            if len(self.calls) == 1:
                raise Exception("Error code: 400 content_filter jailbreak")
            return {"parsed": None}
    llm = FilterOnce()
    asyncio.run(invoke_structured_coach_llm(llm, msgs, context=ctx, system_prompt="SYSTEM", language="he"))
    retry = llm.calls[1]
    assert isinstance(retry[1], SystemMessage) and "שלב נעול" in retry[1].content  # the notes are kept



def test_kamaz_bank_is_whole_and_every_chip_maps_into_its_side():
    from app.bsd_v2.kamaz_bank import DISCOVERY_QUESTIONS, NATURE_TRAITS, SOURCE_TRAITS, normalize_trait, questions_for, side_of
    assert len(SOURCE_TRAITS) == 22 and len(NATURE_TRAITS) == 17
    shorts = [t["short"] for t in SOURCE_TRAITS + NATURE_TRAITS]
    assert len(shorts) == len(set(shorts))
    assert [q["side"] for q in DISCOVERY_QUESTIONS] == ["source"] * 3 + ["nature"] * 3
    assert all(side_of(m) == q["side"] for q in DISCOVERY_QUESTIONS for c in q["chips"] for m in c["maps_to"])
    assert normalize_trait("אמת / כנות") == "כנות" and normalize_trait("עצמאות (נטייה להסתדר לבד)") == "עצמאות"
    assert normalize_trait("פחד מדחייה") is None
    assert "מתמלאת" in questions_for("female")[1]["prompt"] and "מתמלא " in questions_for("male")[1]["prompt"]


def test_kamaz_extraction_keeps_bank_traits_with_his_words_only():
    from app.bsd_v2.kamaz_extract import _Extraction, _Suggestion, validate_extraction
    answers = [{"id": "n1", "side": "nature", "prompt": "כשאני מוותרת…", "text": "אני מפחדת שיכעסו עליי"}]
    raw = _Extraction(
        source=[_Suggestion(trait="חכמה", quote="אני מפחדת שיכעסו עליי")],  # not in the bank
        nature=[_Suggestion(trait="צורך בשייכות וקבלה", quote="כשאני מוותרת… אני מפחדת שיכעסו עליי"),
                _Suggestion(trait="זהירות", quote="אני תמיד בודקת הכול")],  # quote not in his words
        event_nature=["צורך בשייכות וקבלה", "פחד"])
    out = validate_extraction(raw, answers, {})
    assert out["suggested"]["source"] == []
    assert out["suggested"]["nature"] == [{"trait": "צורך בשייכות וקבלה", "quote": "אני מפחדת שיכעסו עליי"}]
    assert out["event_rank"]["nature"] == ["צורך בשייכות וקבלה"]


def test_kamaz_chips_map_without_the_model():
    from app.bsd_v2.kamaz_bank import chip_traits
    out = chip_traits([{"id": "n2", "text": "פחד לטעות ורצון שהכל ייעשה מדויק", "chips_used": ["n2b"]}])
    assert [x["trait"] for x in out["nature"]] == ["יסודיות ודיוק", "שאיפה למצוינות"] and out["source"] == []


def test_kamaz_permission_answer():
    from app.bsd_v2.single_agent_coach import _kamaz_permission_answer as f, _s12_update_permission
    assert f("כן, בשמחה") == "yes" and f("יאללה") == "yes" and f("לא עכשיו") == "no" and f("לא, אני מעדיף לדלג") == "no"
    assert f("למה צריך את זה?") == "question" and f("כן, מה זה אומר?") == "yes"
    state = _v3_state("S12")
    state["messages"] = [_coach("… יש לי רשות להיכנס איתך לגילוי קצר וממוקד של הכוחות האלה?", "S12")]
    _s12_update_permission(state, "למה זה חשוב?")
    assert state["kamaz_permission"] == "question"
    state["messages"].append({"sender": "user", "content": "למה זה חשוב?"})
    state["messages"].append(_coach("כי מתוך הכוחות שלך תבחר עמדה חדשה. יש לי רשות להמשיך?", "S12"))
    _s12_update_permission(state, "אני עדיין לא בטוח למה?")
    assert state["kamaz_permission"] == "yes"  # explained once — go on


def test_request_carries_the_forces_chosen_for_the_event():
    state = _v3_state("S15", forces={"source": ["כנות", "אומץ", "אהבה", "נתינה", "שמחה", "אמונה"],
                                     "nature": ["זהירות", "מחושבות", "עצמאות", "מעשיות", "שמירה על עצמי", "שאיפה למצוינות"]},
                      selected_makor=["אומץ", "כנות"], selected_teva=["מחושבות"])
    tool_call = resolve_post_turn_tool_call("S14", state, ux_version=3)
    assert tool_call["data"]["selected_source"] == ["אומץ", "כנות"] and tool_call["data"]["selected_nature"] == ["מחושבות"]


def test_s12_post_card_note_reflects_the_event_choice():
    from app.bsd_v2.single_agent_coach import build_conversation_context
    state = _v3_state("S12", forces={"source": ["כנות"] * 6, "nature": ["זהירות"] * 6},
                      selected_makor=["אומץ"], selected_teva=["מחושבות"])
    state["messages"] = []
    ctx = build_conversation_context(state, "הכרטיס שלי", "he")
    assert "ראש העיר" in ctx and "'אומץ'" in ctx and "מהמקור: אומץ, ומהטבע: מחושבות" in ctx


def test_cards_carry_the_clients_gender_and_the_request_opens_in_it():
    from app.bsd_v2.coaching_request import compose_coaching_request
    state = _v3_state("S3", event_description="הוא ביטל את הארוחה")
    state["_user_gender"] = "female"
    tool_call = resolve_post_turn_tool_call("S2", state, ux_version=3)
    assert tool_call["tool_type"] == "emotion_selector" and tool_call["data"]["gender"] == "female"
    base = {"situation": "לדבר על מה שאני צריכה", "old": "x", "new": "y", "result": "z"}
    assert compose_coaching_request({**base, "gender": "female"}).startswith("אני מבקשת להתאמן")
    assert compose_coaching_request({**base, "gender": "male"}).startswith("אני מבקש להתאמן")
    assert compose_coaching_request(base).startswith("אני מבקש/ת להתאמן")


def test_stage_insight_quotes_skip_the_stage_button_message():
    import asyncio
    import app.bsd_v2.stage_intro_generator as sig
    seen = {}

    class FakeLLM:
        def with_structured_output(self, *a, **k):
            return self
        async def ainvoke(self, messages):
            seen["prompt"] = "\\n".join(str(getattr(m, "content", "")) for m in messages)
            raise RuntimeError("stop")  # the prompt is what we check
    state = _v3_state("S12")
    state["messages"] = [{"sender": "user", "content": "אני מוכן להתחיל"}, {"sender": "user", "content": "אני רוצה להבין את הכוחות שלי"}]
    orig = sig.get_azure_chat_llm_4o_mini if hasattr(sig, "get_azure_chat_llm_4o_mini") else None
    try:
        if orig:
            sig.get_azure_chat_llm_4o_mini = lambda: FakeLLM()
        try:
            asyncio.run(sig._generate_insight_card(state, {}, "kamaz", True))
        except Exception:
            pass
    finally:
        if orig:
            sig.get_azure_chat_llm_4o_mini = orig
    assert "אני מוכן להתחיל" not in seen["prompt"] and "אני רוצה להבין את הכוחות שלי" in seen["prompt"]


def test_s15_result_naming_the_partner_depends_on_others():
    from app.bsd_v2.single_agent_coach import _people_names, _result_issue
    names = _people_names({"event_description": "מוצאי שבת — עם איתי, בעלי — ביקשתי מאיתי שיעזור"})
    assert names == ("איתי",)
    assert _result_issue("אסביר בלי להרים קול פעמיים בשבוע, ואיתי מגיב בשיחה במקום לברוח", names) == "others"
    assert _result_issue("אדבר בשקט פעמיים בשבוע כדי שאיתי יקשיב", names) == "others"
    # a condition on the partner, then the client's own step — in his hands
    assert _result_issue("בפעם הבאה שאיתי ידבר בטון חריף, אסביר בשקט שאני צריך זמן, שלוש פעמים החודש", names) == ""


def test_resume_brings_back_the_card_the_coach_was_waiting_for():
    from app.bsd_v2.stage_tool_triggers import pending_card_on_resume

    def state(step, coach, **cd):
        return {"ux_version": 3, "current_step": step, "collected_data": cd,
                "messages": [{"sender": "user", "content": "x"}, {"sender": "coach", "content": coach}]}

    # pilot Oct 30: after the רצוי card the coach announced the gap — a fresh window showed no card
    lead_in = "באותו רגע היית רוצה להרגיש רוגע. עכשיו נבדוק יחד מה הפער בין מה שהיה לבין מה שהיית רוצה."
    assert pending_card_on_resume(state("S7", lead_in, action_desired="לחבק"))["tool_type"] == "gap_card"
    # the card was submitted, the coach now asks the booklet question in the chat
    assert pending_card_on_resume(state("S7", "האם את מאמינה שבפער הזה יש משהו טוב בשבילך?", gap_name="כבוד")) is None
    assert pending_card_on_resume(state("S7", lead_in, gap_name="כבוד")) is None
    # a question is answered in the chat — except the event card, the only way into the process
    assert pending_card_on_resume(state("S6", "מה היית רוצה?")) is None
    assert pending_card_on_resume(state("S2", "מה בדיוק קרה שם?"))["tool_type"] == "event_form"
    assert pending_card_on_resume(state("S5", "זו התגובה שלך באותו רגע.", action_actual="צעקתי"))["tool_type"] == "matzui_summary"
    assert pending_card_on_resume(state("S11", "עכשיו נבדוק מה העמדה נותנת לך.", stance={"gains": []}))["tool_type"] == "balance_scale"
    assert pending_card_on_resume(state("S4", "מה עבר לך בראש?")) is None  # S4 has no card
    assert pending_card_on_resume({**state("S7", lead_in), "ux_version": 2}) is None
