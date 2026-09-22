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
    "S8": "s7_pattern.md",     # דפוס
    "S9": "s7_paradigm.md",    # פרדיגמה (מחשבת המעשה)
    "S10": "s8_stance_trigger.md",  # עמדה + טריגר
    "S11": "s8_stance.md",     # רווחים והפסדים
    "S12": "s9_forces.md", "S13": "s10_choice.md", "S14": "s11_vision.md", "S15": "s12_commitment.md",
}

# V3 stage prompts — shorter, tool-aware versions for hybrid UI.
# When ux_version >= 3 and a V3 prompt exists, it replaces the V2 stage prompt.
# Stages without a V3 prompt (S4, S8, S14) use the V2 prompt as-is.
V3_STAGE_FILES: Dict[str, str] = {
    "S2": "v3/s2_event.md",
    "S3": "v3/s3_emotions.md",
    "S5": "v3/s5_action.md",
    "S6": "v3/s6_desired.md",
    "S7": "v3/s7_gap.md",
    "S9": "v3/s9_paradigm_stance.md",   # merged S9+S10
    "S10": "v3/s9_paradigm_stance.md",  # same file — V3 merges these stages
    "S11": "v3/s11_gains_losses.md",
    "S12": "v3/s12_forces.md",
    "S13": "v3/s13_choice.md",
    "S15": "v3/s15_commitment.md",
}

SUPPORTED_LANGUAGES = {"he", "en"}

# Per-stage collected_data instructions — only the relevant fields.
# Keeps the prompt focused so the model doesn't get ideas about other stages.
STAGE_COLLECTED_DATA_HE: Dict[str, str] = {
    "S0": "`collected_data`: אין שדות לעדכן ב-S0.",
    "S1": "`collected_data`: מלא `topic` — נושא האימון במשפט קצר.",
    "S2": "`collected_data`: מלא `event_description` (תיאור האירוע). עדכן גם `topic` אם המתאמן חידד.",
    "S3": "`collected_data`: מלא `emotions` — רשימת רגשות שהמשתמש הביע.",
    "S4": "`collected_data`: מלא `thought` — המשפט הפנימי / מחשבה באותו רגע.",
    "S5": "`collected_data`: מלא `action_actual` — מה עשה בפועל (מצוי).",
    "S6": "`collected_data`: מלא `action_desired`, `emotion_desired`, `thought_desired` — מה היה רוצה לעשות/להרגיש/לחשוב (רצוי).",
    "S7": "`collected_data`: מלא `gap_name` (שם הפער), `gap_score` (ציון 1-10), `gap_booklet_moves` (מערך: belief, opportunity, dwelling, authenticity — עדכן מצטבר).",
    "S8": "`collected_data`: מלא `pattern` — הדפוס החוזר שזוהה.",
    "S9": "`collected_data`: מלא `paradigm` — הפרדיגמה / מחשבת המעשה ('ככה זה אצלי').",
    "S10": "`collected_data`: ב־`stance` מלא `reality_belief` (תפיסת מציאות) ו-`activation_trigger` (טריגר).",
    "S11": "`collected_data`: ב־`stance` מלא `gains` ו-`losses` (טבלת רווח והפסד).",
    "S12": "`collected_data`: מלא `forces` — `source` (מקור) ו-`nature` (טבע); יעד 6+6, ראשון = מובילה. `offer_trait_picker`: true רק כשיש ריכוז ברור לשני הצדדים.",
    "S13": "`collected_data`: מלא `renewal` — בחירה/עמדה חדשה. תמהיל כמ\"ז באחוזים.",
    "S14": "`collected_data`: מלא `vision` — חזון / תמונת עתיד.",
    "S15": "`collected_data`: מלא `commitment` — צעד מחויבות קונקרטי.",
}
STAGE_COLLECTED_DATA_EN: Dict[str, str] = {
    "S0": "`collected_data`: No fields to update in S0.",
    "S1": "`collected_data`: Fill `topic` — short coaching topic sentence.",
    "S2": "`collected_data`: Fill `event_description`. Also update `topic` if the user refined it.",
    "S3": "`collected_data`: Fill `emotions` — list of emotions the user expressed.",
    "S4": "`collected_data`: Fill `thought` — the inner sentence / thought in that moment.",
    "S5": "`collected_data`: Fill `action_actual` — what the user actually did.",
    "S6": "`collected_data`: Fill `action_desired`, `emotion_desired`, `thought_desired`.",
    "S7": "`collected_data`: Fill `gap_name`, `gap_score`, `gap_booklet_moves` (cumulative array).",
    "S8": "`collected_data`: Fill `pattern` — the recurring pattern identified.",
    "S9": "`collected_data`: Fill `paradigm` — 'that's how it is for me'.",
    "S10": "`collected_data`: In `stance`, fill `reality_belief` and `activation_trigger`.",
    "S11": "`collected_data`: In `stance`, fill `gains` and `losses`.",
    "S12": "`collected_data`: Fill `forces` — `source` and `nature`; target 6+6, first = leading trait. `offer_trait_picker`: true only with clear summary for both sides.",
    "S13": "`collected_data`: Fill `renewal` — new choice/stance. KaMaZ mix in percentages.",
    "S14": "`collected_data`: Fill `vision` — future picture.",
    "S15": "`collected_data`: Fill `commitment` — concrete first step.",
}

# Gate per stage only – each stage sees only its transition rule
STAGE_GATES_HE: Dict[str, str] = {
    "S0": "**Gate (S0→S1):** רשות מפורשת להתחיל (כן/בסדר/בוא נתחיל).",
    "S1": "**Gate (S1→S2):** נושא ברור אחרי 2–3 תורות (מספיק להבין על מה להתאמן).",
    "S2": "**Gate (S2→S3):** אירוע ספציפי עם מתי/איפה/עם מי/מה קרה — **קשר אינטראקטיבי** (לא רק נוכחות משותפת).",
    "S3": "**Gate (S3→S4):** 2 רגשות — מספיק, עבור ל-S4.",
    "S4": "**Gate (S4→S5):** משפט מחשבה ברור באותו רגע.",
    "S5": "**Gate (S5→S6):** מעשה בפועל ברור.",
    "S6": "**Gate (S6→S7):** יש רצוי (מעשה+רגש+מחשבה)? → סכם בקצרה ועבור מיד ל-S7. אין צורך באישור נפרד.",
    "S7": "**Gate (S7→S8):** שם + ציון + אמונה + הזדמנות נשאלו? → עבור מיד ל-S8. אין שאלות נוספות.",
    "S8": "**Gate (S8→S9):** דפוס סוכם + אישור משתמש.",
    "S9": "**Gate (S9→S10):** פרדיגמה מנוסחת עם 'ככה זה אצלי'.",
    "S10": "**Gate (S10→S11):** עמדה מנוסחת + טריגר + שאלות שליטה/סביבה.",
    "S11": "**Gate (S11→S12):** 2+ רווחים, 2+ הפסדים.",
    "S12": "**Gate (S12→S13):** חקר מקור (מאקרו) ואז טבע (מאקרו) — בלי עיגון לאירוע האימון; ב־`forces` **6+6** + **מובילה ראשונה** בכל רשימה; או **הסכמה מפורשת** לקיצור (ב־`reflection`). המערכת חוסמת מעבר בלי זה.",
    "S13": "**Gate (S13→S14):** `renewal` מלא (עמדה חדשה) + המתאמן תיאר לפחות פרדיגמה או דפוס חדשים. תמהיל כמ\"ז רצוי אך לא חוסם.",
    "S14": "**Gate (S14→S15):** חזון ברור.",
    "S15": "**Gate (S15→סיום):** מחויבות קונקרטית.",
}
STAGE_GATES_EN: Dict[str, str] = {
    "S0": "**Gate (S0→S1):** Explicit permission to start (yes/okay/let's go).",
    "S1": "**Gate (S1→S2):** Clear topic after 2–3 turns.",
    "S2": "**Gate (S2→S3):** Specific event with when/where/who/what — **interactive contact** (not just co-presence).",
    "S3": "**Gate (S3→S4):** 2 emotions — enough, advance to S4.",
    "S4": "**Gate (S4→S5):** Clear thought sentence in that moment.",
    "S5": "**Gate (S5→S6):** Clear actual action.",
    "S6": "**Gate (S6→S7):** Desired (action+emotion+thought) collected? → Summarize briefly and advance to S7 immediately. No separate approval needed.",
    "S7": "**Gate (S7→S8):** Name + score + belief + opportunity asked? → Advance to S8 immediately. No more questions.",
    "S8": "**Gate (S8→S9):** Pattern summarized + user confirmation.",
    "S9": "**Gate (S9→S10):** Paradigm formulated with 'that's how it is for me'.",
    "S10": "**Gate (S10→S11):** Stance formulated + trigger + control/environment questions.",
    "S11": "**Gate (S11→S12):** 2+ gains, 2+ losses.",
    "S12": "**Gate (S12→S13):** Source (macro life), then nature (macro) — not anchored to the coaching-event story; in `forces` **6+6** + **first item** = leading trait each side; or **explicit** consent to a shorter card (in `reflection`). The API blocks the transition without this.",
    "S13": "**Gate (S13→S14):** `renewal` filled (new stance) + user described at least paradigm or pattern. KaMaZ mix encouraged but not blocking.",
    "S14": "**Gate (S14→S15):** Clear vision.",
    "S15": "**Gate (S15→End):** Specific commitment.",
}


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


_V3_TOOL_DATA_KEYS: Dict[str, str] = {
    "S2": "event_description",
    "S3": "emotions",
    "S5": "action_actual",
    "S6": "action_desired",
    "S7": "gap_name",
    "S9": "paradigm",
    "S10": "paradigm",
    "S11": "stance",
    "S12": "forces",
    "S13": "renewal",
    "S15": "commitment",
}


def assemble_system_prompt(current_step: str, language: str = "he", user_gender: str = None, ux_version: int = 2, collected_data: dict = None) -> str:
    """Assemble focused prompt for current stage and language.
    user_gender: 'male', 'female', or None - from user dashboard. Affects אתה/את etc.
    ux_version: 2 or 3 - when 3, includes v3_hybrid_addon.md.
    collected_data: current collected_data dict — used in V3 to detect pre-tool vs post-tool."""
    lang = _normalize_language(language)
    prompts_dir = Path(__file__).parent
    core_dir = prompts_dir / "core"
    stages_dir = prompts_dir / "stages"

    core_files: List[str] = [
        "persona.md",
        "coach_charter.md",
        "process_map.md",
        "response_format.md",
    ]

    core_sections = []
    for core_file in core_files:
        resolved = _resolve_prompt_file(core_dir, lang, core_file)
        core_sections.append(_load_file(str(resolved)).strip())

    # V3 hybrid addon: include extra instructions for structured UI
    if ux_version >= 3:
        v3_addon_path = core_dir / "v3_hybrid_addon.md"
        if v3_addon_path.exists():
            core_sections.append(_load_file(str(v3_addon_path)).strip())

    # Inject only the gate relevant for THIS stage
    gates_dict = STAGE_GATES_HE if lang == "he" else STAGE_GATES_EN
    gate_content = gates_dict.get(current_step, "")
    safety_he = "**Safety:** אל תחזור על שאלות. \"אמרתי כבר\" → התנצל ועבור. שאל בלבד."
    safety_en = "**Safety:** No repeated questions. \"I already said\" → Apologize and move on. Questions only."
    gate_section = f"\n\n{gate_content}\n\n---\n\n{safety_he if lang == 'he' else safety_en}"

    # V3: choose between pre-tool prompt (data not yet collected) and post-tool prompt (data collected)
    if ux_version >= 3 and current_step in V3_STAGE_FILES:
        cd = collected_data or {}
        data_key = _V3_TOOL_DATA_KEYS.get(current_step)
        tool_data_present = False
        if data_key and cd.get(data_key):
            val = cd[data_key]
            tool_data_present = bool(val) and val != [] and val != {}

        if tool_data_present:
            # Post-tool: use V3 validation prompt
            v3_file = V3_STAGE_FILES[current_step]
            v3_path = stages_dir / v3_file
            if v3_path.exists():
                stage_content = _load_file(str(v3_path)).strip()
            else:
                stage_file = STAGE_FILES.get(current_step, "s1_topic.md")
                stage_path = _resolve_prompt_file(stages_dir, lang, stage_file)
                stage_content = _load_file(str(stage_path)).strip()
        else:
            # Pre-tool: brief warm transition before the UI card appears
            pre_tool_path = stages_dir / "v3" / "pre_tool.md"
            if pre_tool_path.exists():
                stage_content = _load_file(str(pre_tool_path)).strip()
            else:
                stage_file = STAGE_FILES.get(current_step, "s1_topic.md")
                stage_path = _resolve_prompt_file(stages_dir, lang, stage_file)
                stage_content = _load_file(str(stage_path)).strip()
    else:
        stage_file = STAGE_FILES.get(current_step, "s1_topic.md")
        stage_path = _resolve_prompt_file(stages_dir, lang, stage_file)
        stage_content = _load_file(str(stage_path)).strip()

    stage_title = f"# שלב נוכחי: {current_step}" if lang == "he" else f"# Current Stage: {current_step}"
    response_format = core_sections[-1]

    # Append stage-specific collected_data instruction to response format
    cd_dict = STAGE_COLLECTED_DATA_HE if lang == "he" else STAGE_COLLECTED_DATA_EN
    cd_instruction = cd_dict.get(current_step, "")
    if cd_instruction:
        response_format = response_format + f"\n\n{cd_instruction}"

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

    # Core: persona + process_map, then stage-specific gate only
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
