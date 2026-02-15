"""
BSD V2 - Dynamic Prompt Manager
Assembles stage-specific prompts on-the-fly for performance optimization.
"""

import os
from pathlib import Path
from typing import Dict
from functools import lru_cache

STAGE_FILES: Dict[str, str] = {
    "S0": "s0_contract.md", "S1": "s1_topic.md", "S2": "s2_event.md",
    "S3": "s3_emotions.md", "S4": "s4_thought.md", "S5": "s5_action_desired.md",
    "S6": "s6_gap.md", "S7": "s7_pattern.md", "S8": "s8_stance.md",
    "S9": "s9_forces.md", "S10": "s10_choice.md", "S11": "s11_vision.md",
    "S12": "s12_commitment.md",
}

@lru_cache(maxsize=32)
def _load_file(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def assemble_system_prompt(current_step: str) -> str:
    """Assemble focused prompt for current stage."""
    prompts_dir = Path(__file__).parent
    core_dir = prompts_dir / "core"
    stages_dir = prompts_dir / "stages"
    
    persona = _load_file(str(core_dir / "persona.md"))
    response_format = _load_file(str(core_dir / "response_format.md"))
    
    stage_file = STAGE_FILES.get(current_step, "s1_topic.md")
    stage_content = _load_file(str(stages_dir / stage_file))
    
    return f"""{persona}

---

# שלב נוכחי: {current_step}

{stage_content}

---

{response_format}
"""

def get_prompt_stats(current_step: str) -> Dict[str, int]:
    prompt = assemble_system_prompt(current_step)
    words = len(prompt.split())
    return {
        "chars": len(prompt),
        "words": words,
        "estimated_tokens": int(words * 1.7)
    }
