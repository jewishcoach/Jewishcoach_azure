#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple prompt validation for markdown prompt_manager.
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


def test_prompts() -> bool:
    """Validate structure and size for all stages/languages."""
    print("=" * 80)
    print("TESTING MARKDOWN PROMPTS")
    print("=" * 80)
    print()

    stages = [f"S{i}" for i in range(13)]
    languages = ["he", "en"]
    all_ok = True

    for lang in languages:
        lang_name = "Hebrew" if lang == "he" else "English"
        print(f"\n{lang_name} Prompts:")
        print("-" * 80)

        for stage in stages:
            try:
                prompt = assemble_system_prompt(stage, language=lang)
                stats = get_prompt_stats(stage, language=lang)
                has_overview = ("BSD" in prompt) or ("בני" in prompt)
                has_stage = stage in prompt
                has_format = ("coach_message" in prompt) and ("internal_state" in prompt)
                tokens = stats["estimated_tokens"]

                if has_overview and has_stage and has_format:
                    status = "OK"
                else:
                    status = "FAIL"
                    all_ok = False

                print(
                    f"   [{status}] {stage}: {tokens:>4} tokens | "
                    f"Overview: {'Y' if has_overview else 'N'} | "
                    f"Stage: {'Y' if has_stage else 'N'} | "
                    f"Format: {'Y' if has_format else 'N'}"
                )
            except Exception as exc:
                print(f"   [FAIL] {stage}: ERROR - {exc}")
                all_ok = False

    return all_ok


def test_prompt_content() -> bool:
    """Validate key BSD concepts are present in core stages."""
    print("\n" + "=" * 80)
    print("TESTING PROMPT CONTENT")
    print("=" * 80)
    print()

    s2_he = assemble_system_prompt("S2", language="he")
    s7_he = assemble_system_prompt("S7", language="he")

    key_concepts_s2 = ["4 תנאים", "זמן", "מעורבות", "רגש", "אנשים", "לא חייב"]
    key_concepts_s7 = ["דפוס", "תגובה", "מצבים", "אישור"]

    all_present = True
    print("S2 concepts:")
    for concept in key_concepts_s2:
        if concept in s2_he:
            print(f"   [OK] {concept}")
        else:
            print(f"   [MISS] {concept}")
            all_present = False

    print("\nS7 concepts:")
    for concept in key_concepts_s7:
        if concept in s7_he:
            print(f"   [OK] {concept}")
        else:
            print(f"   [MISS] {concept}")
            all_present = False

    return all_present


if __name__ == "__main__":
    ok_structure = test_prompts()
    ok_content = test_prompt_content()

    print("\n" + "=" * 80)
    if ok_structure and ok_content:
        print("ALL VALIDATIONS PASSED")
        raise SystemExit(0)

    print("SOME VALIDATIONS FAILED")
    raise SystemExit(1)
