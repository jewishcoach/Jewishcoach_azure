"""
BSD V2 - Dynamic Prompt Manager
Assembles stage-specific prompts on-the-fly for performance optimization.
"""

from pathlib import Path
from typing import Dict, List
from functools import lru_cache

STAGE_FILES: Dict[str, str] = {
    "S0": "s0_contract.md", "S1": "s1_topic.md", "S2": "s2_event.md",
    "S3": "s3_emotions.md", "S4": "s4_thought.md",
    "S5": "s5_action.md",       # מצוי - מעשה בלבד
    "S6": "s6_desired.md",     # רצוי - רגש, מחשבה, מעשה
    "S7": "s6_gap.md",         # פער
    "S8": "s7_pattern.md", "S9": "s8_stance.md", "S10": "s9_forces.md",
    "S11": "s10_choice.md", "S12": "s11_vision.md", "S13": "s12_commitment.md",
}

SUPPORTED_LANGUAGES = {"he", "en"}


@lru_cache(maxsize=256)
def _load_file(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def _normalize_language(language: str) -> str:
    if not language:
        return "he"
    normalized = language.lower().strip()
    if normalized.startswith("he"):
        return "he"
    if normalized.startswith("en"):
        return "en"
    return "he"


def _resolve_prompt_file(base_dir: Path, language: str, filename: str) -> Path:
    """
    Resolve prompt file with backward compatibility.
    Preferred: <base>/<language>/<filename>
    Fallback:  <base>/<filename>
    """
    lang_path = base_dir / language / filename
    if lang_path.exists():
        return lang_path

    legacy_path = base_dir / filename
    if legacy_path.exists():
        return legacy_path

    raise FileNotFoundError(f"Prompt file not found for language={language}: {filename}")


def assemble_system_prompt(current_step: str, language: str = "he") -> str:
    """Assemble focused prompt for current stage and language."""
    lang = _normalize_language(language)
    prompts_dir = Path(__file__).parent
    core_dir = prompts_dir / "core"
    stages_dir = prompts_dir / "stages"

    core_files: List[str] = [
        "persona.md",
        "process_map.md",
        "meta_questions.md",
        "gates.md",
        "response_format.md",
    ]

    core_sections = []
    for core_file in core_files:
        resolved = _resolve_prompt_file(core_dir, lang, core_file)
        core_sections.append(_load_file(str(resolved)).strip())

    stage_file = STAGE_FILES.get(current_step, "s1_topic.md")
    stage_path = _resolve_prompt_file(stages_dir, lang, stage_file)
    stage_content = _load_file(str(stage_path)).strip()

    stage_title = f"# שלב נוכחי: {current_step}" if lang == "he" else f"# Current Stage: {current_step}"

    return f"""{'\n\n---\n\n'.join(core_sections[:-1])}

---

{stage_title}

{stage_content}

---

{core_sections[-1]}
"""


def get_prompt_stats(current_step: str, language: str = "he") -> Dict[str, int]:
    prompt = assemble_system_prompt(current_step, language=language)
    words = len(prompt.split())
    return {
        "chars": len(prompt),
        "words": words,
        "estimated_tokens": int(words * 1.7)
    }
