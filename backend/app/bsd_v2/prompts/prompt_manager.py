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

# Gate per stage only – each stage sees only ITS transition rule
STAGE_GATES_HE: Dict[str, str] = {
    "S0": "**Gate (S0→S1):** רשות מפורשת להתחיל (כן/בסדר/בוא נתחיל).",
    "S1": "**Gate (S1→S2):** נושא ברור אחרי 2–3 תורות (מספיק להבין על מה להתאמן).",
    "S2": "**Gate (S2→S3):** אירוע ספציפי עם מתי/איפה/עם מי/מה קרה.",
    "S3": "**Gate (S3→S4):** 3–4 רגשות עם עומק חווייתי.",
    "S4": "**Gate (S4→S5):** משפט מחשבה ברור באותו רגע.",
    "S5": "**Gate (S5→S6):** מעשה בפועל ברור.",
    "S6": "**Gate (S6→S7):** רצוי (מעשה+רגש+מחשבה) + סיכום מאושר.",
    "S7": "**Gate (S7→S8):** שם לפער + ציון 1–10.",
    "S8": "**Gate (S8→S9):** דפוס סוכם + אישור משתמש.",
    "S9": "**Gate (S9→S10):** 2+ רווחים, 2+ הפסדים.",
    "S10": "**Gate (S10→S11):** 2+ ערכים, 2+ יכולות.",
    "S11": "**Gate (S11→S12):** בחירה ברורה.",
    "S12": "**Gate (S12→S13):** חזון ברור.",
    "S13": "**Gate (S13→סיום):** מחויבות קונקרטית.",
}
STAGE_GATES_EN: Dict[str, str] = {
    "S0": "**Gate (S0→S1):** Explicit permission to start (yes/okay/let's go).",
    "S1": "**Gate (S1→S2):** Clear topic after 2–3 turns.",
    "S2": "**Gate (S2→S3):** Specific event with when/where/who/what.",
    "S3": "**Gate (S3→S4):** 3–4 emotions with experiential depth.",
    "S4": "**Gate (S4→S5):** Clear thought sentence in that moment.",
    "S5": "**Gate (S5→S6):** Clear actual action.",
    "S6": "**Gate (S6→S7):** Desired (action+emotion+thought) + confirmed summary.",
    "S7": "**Gate (S7→S8):** Gap name + 1–10 score.",
    "S8": "**Gate (S8→S9):** Pattern summarized + user confirmation.",
    "S9": "**Gate (S9→S10):** 2+ gains, 2+ losses.",
    "S10": "**Gate (S10→S11):** 2+ values, 2+ abilities.",
    "S11": "**Gate (S11→S12):** Clear choice.",
    "S12": "**Gate (S12→S13):** Clear vision.",
    "S13": "**Gate (S13→End):** Specific commitment.",
}


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


def assemble_system_prompt(current_step: str, language: str = "he", user_gender: str = None) -> str:
    """Assemble focused prompt for current stage and language.
    user_gender: 'male', 'female', or None - from user dashboard. Affects אתה/את etc."""
    lang = _normalize_language(language)
    prompts_dir = Path(__file__).parent
    core_dir = prompts_dir / "core"
    stages_dir = prompts_dir / "stages"

    core_files: List[str] = [
        "persona.md",
        "process_map.md",
        "meta_questions.md",
        "response_format.md",
    ]

    core_sections = []
    for core_file in core_files:
        resolved = _resolve_prompt_file(core_dir, lang, core_file)
        core_sections.append(_load_file(str(resolved)).strip())

    # Inject only the gate relevant for THIS stage
    gates_dict = STAGE_GATES_HE if lang == "he" else STAGE_GATES_EN
    gate_content = gates_dict.get(current_step, "")
    safety_he = "**Safety:** אל תחזור על שאלות. \"אמרתי כבר\" → התנצל ועבור. שאל בלבד."
    safety_en = "**Safety:** No repeated questions. \"I already said\" → Apologize and move on. Questions only."
    gate_section = f"\n\n{gate_content}\n\n---\n\n{safety_he if lang == 'he' else safety_en}"

    stage_file = STAGE_FILES.get(current_step, "s1_topic.md")
    stage_path = _resolve_prompt_file(stages_dir, lang, stage_file)
    stage_content = _load_file(str(stage_path)).strip()

    stage_title = f"# שלב נוכחי: {current_step}" if lang == "he" else f"# Current Stage: {current_step}"
    response_format = core_sections[-1]

    # Gender instruction (from user dashboard) - critical for correct אתה/את
    gender_suffix = ""
    if lang == "he" and user_gender:
        if user_gender == "female":
            gender_suffix = "\n\n**מגדר:** המתאמן/ת היא אישה. פנה אליה ב'את' (לא 'אתה')."
        elif user_gender == "male":
            gender_suffix = "\n\n**מגדר:** המתאמן/ת הוא גבר. פנה אליו ב'אתה' (לא 'את')."
    elif lang == "en" and user_gender:
        if user_gender == "female":
            gender_suffix = "\n\n**Gender:** The coachee is female."
        elif user_gender == "male":
            gender_suffix = "\n\n**Gender:** The coachee is male."

    # Core: persona + process_map + meta_questions, then stage-specific gate only
    core_text = "\n\n---\n\n".join(core_sections[:-1])
    return f"""{core_text}{gender_suffix}{gate_section}

{stage_title}

{response_format}

---

{stage_content}
"""


def get_prompt_stats(current_step: str, language: str = "he") -> Dict[str, int]:
    prompt = assemble_system_prompt(current_step, language=language)
    words = len(prompt.split())
    return {
        "chars": len(prompt),
        "words": words,
        "estimated_tokens": int(words * 1.7)
    }
