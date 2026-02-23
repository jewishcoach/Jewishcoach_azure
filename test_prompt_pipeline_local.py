#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local prompt/state integration test without LLM dependencies.

Validates:
1) prompt_manager can assemble prompts for all stages/languages
2) state_schema can absorb staged internal_state updates
3) collected_data full schema remains compatible across progression
"""

import importlib.util
from pathlib import Path


PROMPT_MANAGER_PATH = Path("/home/ishai/code/Jewishcoach_azure/backend/app/bsd_v2/prompts/prompt_manager.py")
spec = importlib.util.spec_from_file_location("prompt_manager", PROMPT_MANAGER_PATH)
prompt_manager = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(prompt_manager)

assemble_system_prompt = prompt_manager.assemble_system_prompt

STATE_SCHEMA_PATH = Path("/home/ishai/code/Jewishcoach_azure/backend/app/bsd_v2/state_schema_v2.py")
state_spec = importlib.util.spec_from_file_location("state_schema_v2", STATE_SCHEMA_PATH)
state_schema_v2 = importlib.util.module_from_spec(state_spec)
assert state_spec and state_spec.loader
state_spec.loader.exec_module(state_schema_v2)
create_initial_state = state_schema_v2.create_initial_state
add_message = state_schema_v2.add_message


REQUIRED_SCHEMA_KEYS = {
    "topic",
    "event_description",
    "emotions",
    "thought",
    "action_actual",
    "action_desired",
    "emotion_desired",
    "thought_desired",
    "gap_name",
    "gap_score",
    "pattern",
    "stance",
    "forces",
    "renewal",
    "vision",
    "commitment",
}


def validate_prompt_assembly() -> bool:
    stages = [f"S{i}" for i in range(13)]
    languages = ["he", "en"]
    ok = True

    print("=" * 80)
    print("PROMPT ASSEMBLY CHECK")
    print("=" * 80)

    for lang in languages:
        for stage in stages:
            try:
                prompt = assemble_system_prompt(stage, language=lang)
                if stage not in prompt:
                    print(f"[FAIL] Missing stage marker: {lang}/{stage}")
                    ok = False
                if "coach_message" not in prompt or "internal_state" not in prompt:
                    print(f"[FAIL] Missing JSON format section: {lang}/{stage}")
                    ok = False
            except Exception as exc:
                print(f"[FAIL] Assembly error {lang}/{stage}: {exc}")
                ok = False

    if ok:
        print("[OK] Prompt assembly succeeded for all stages/languages")
    return ok


def validate_state_progression() -> bool:
    print("\n" + "=" * 80)
    print("STATE PROGRESSION CHECK")
    print("=" * 80)

    state = create_initial_state(conversation_id="local_test", user_id="tester", language="he")

    simulated_turns = [
        (
            "S1",
            {"topic": "זוגיות", "event_description": None},
            0.6,
        ),
        (
            "S2",
            {"event_description": "שיחה עם בת הזוג לפני שבועיים", "topic": "זוגיות"},
            0.8,
        ),
        (
            "S3",
            {"emotions": ["תסכול", "פחד", "אשמה"]},
            0.9,
        ),
        (
            "S4",
            {"thought": "אני לא מספיק טוב"},
            0.8,
        ),
        (
            "S5",
            {
                "action_actual": "שתקתי",
                "action_desired": "לשתף בצורה רגועה",
                "emotion_desired": "בטוח",
                "thought_desired": "אני יכול לדבר ברור",
            },
            0.9,
        ),
        (
            "S6",
            {"gap_name": "הימנעות", "gap_score": 8},
            0.8,
        ),
        (
            "S7",
            {"pattern": "כשיש לחץ אני שותק ומתרחק"},
            0.9,
        ),
        (
            "S8",
            {"stance": {"gains": ["נמנע מריב"], "losses": ["מתרחק"]}},
            0.8,
        ),
        (
            "S9",
            {"forces": {"source": ["כנות"], "nature": ["אומץ"]}},
            0.8,
        ),
        (
            "S10",
            {"renewal": "אני בוחר לדבר במקום להימנע"},
            0.8,
        ),
        (
            "S11",
            {"vision": "קשר פתוח ובטוח יותר"},
            0.8,
        ),
        (
            "S12",
            {"commitment": "היום בערב אשתף במשפט פתיחה"},
            1.0,
        ),
    ]

    for idx, (step, delta, saturation) in enumerate(simulated_turns, start=1):
        state = add_message(state, "user", f"user turn {idx}")
        internal_state = {
            "current_step": step,
            "saturation_score": saturation,
            "collected_data": delta,
        }
        state = add_message(state, "coach", f"coach turn {idx}", internal_state)

    schema_keys = set(state["collected_data"].keys())
    if REQUIRED_SCHEMA_KEYS - schema_keys:
        print(f"[FAIL] Missing collected_data keys: {sorted(REQUIRED_SCHEMA_KEYS - schema_keys)}")
        return False

    if state["current_step"] != "S12":
        print(f"[FAIL] Expected final step S12, got {state['current_step']}")
        return False

    if state["collected_data"]["gap_name"] != "הימנעות":
        print("[FAIL] gap_name was not preserved")
        return False

    if not state["collected_data"]["commitment"]:
        print("[FAIL] commitment missing at final stage")
        return False

    print("[OK] State progression and schema compatibility validated")
    return True


if __name__ == "__main__":
    ok_prompt = validate_prompt_assembly()
    ok_state = validate_state_progression()
    print("\n" + "=" * 80)
    if ok_prompt and ok_state:
        print("LOCAL PIPELINE TEST PASSED")
        raise SystemExit(0)

    print("LOCAL PIPELINE TEST FAILED")
    raise SystemExit(1)
