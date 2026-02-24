#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prompt manager smoke tests for BSD V2 modular markdown prompts.
"""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
PROMPT_MANAGER_PATH = REPO_ROOT / "backend/app/bsd_v2/prompts/prompt_manager.py"
spec = importlib.util.spec_from_file_location("prompt_manager", PROMPT_MANAGER_PATH)
prompt_manager = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(prompt_manager)
assemble_system_prompt = prompt_manager.assemble_system_prompt
get_prompt_stats = prompt_manager.get_prompt_stats


STAGES = [f"S{i}" for i in range(13)]
LANGUAGES = ["he", "en"]


def test_prompt_assembly() -> bool:
    ok = True
    print("=" * 80)
    print("TESTING PROMPT MANAGER ASSEMBLY")
    print("=" * 80)

    for lang in LANGUAGES:
        print(f"\nLanguage: {lang}")
        for stage in STAGES:
            try:
                prompt = assemble_system_prompt(stage, language=lang)
                stats = get_prompt_stats(stage, language=lang)
                has_stage = stage in prompt
                has_json = "coach_message" in prompt and "internal_state" in prompt
                status = "OK" if has_stage and has_json else "FAIL"
                print(f"  [{status}] {stage}: ~{stats['estimated_tokens']} tokens")
                if not (has_stage and has_json):
                    ok = False
            except Exception as exc:
                print(f"  [FAIL] {stage}: {exc}")
                ok = False

    return ok


def test_schema_keys_present() -> bool:
    print("\n" + "=" * 80)
    print("TESTING COLLECTED_DATA SCHEMA (Azure-optimized: topic only)")
    print("=" * 80)

    prompt = assemble_system_prompt("S1", language="he")
    # Azure-optimized: minimal JSON - only topic in collected_data
    required = ["coach_message", "current_step", "saturation_score", "collected_data", "topic", "reflection"]
    missing = [key for key in required if key not in prompt]
    if missing:
        print(f"[FAIL] Missing keys: {missing}")
        return False

    print("[OK] Required schema keys present (coach_message, internal_state, collected_data.topic)")
    return True


if __name__ == "__main__":
    assembly_ok = test_prompt_assembly()
    schema_ok = test_schema_keys_present()
    print("\n" + "=" * 80)
    if assembly_ok and schema_ok:
        print("ALL PROMPT MANAGER TESTS PASSED")
        raise SystemExit(0)
    print("PROMPT MANAGER TESTS FAILED")
    raise SystemExit(1)
