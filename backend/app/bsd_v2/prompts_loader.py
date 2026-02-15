# -*- coding: utf-8 -*-
"""
Prompts Loader - Safe JSON-based prompt loading for Azure
Separates Hebrew strings from code to avoid encoding issues
"""

import json
import os
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def load_prompts():
    """Load prompts from JSON file (cached)."""
    try:
        prompts_path = os.path.join(os.path.dirname(__file__), 'prompts.json')
        with open(prompts_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"✅ Loaded prompts from {prompts_path}")
        return data
    except Exception as e:
        logger.error(f"❌ Failed to load prompts.json: {e}")
        # Fallback to minimal prompt
        return {
            "core_persona": "אתה בני מאמן בשיטת BSD",
            "stages": {f"S{i}": f"שלב S{i}" for i in range(13)},
            "response_format": "החזר JSON"
        }

def get_focused_prompt(stage: str) -> str:
    """
    Build focused prompt for specific stage.
    
    Structure:
    - Core persona (always)
    - Stage-specific instructions (current stage only)
    - Response format (always)
    
    Result: ~1,200 tokens vs 6,672
    """
    prompts = load_prompts()
    
    core = prompts.get("core_persona", "")
    stage_content = prompts.get("stages", {}).get(stage, prompts["stages"].get("S1", ""))
    response_fmt = prompts.get("response_format", "")
    
    return f"""{core}

# ══════════════════════════════════════════════════════════════════════════════
# שלב נוכחי: {stage}
# ══════════════════════════════════════════════════════════════════════════════

{stage_content}

{response_fmt}
"""

if __name__ == "__main__":
    # Test
    print("Testing prompts loader...")
    p = load_prompts()
    print(f"✅ Loaded {len(p.get('stages', {}))} stages")
    
    for stage in ["S1", "S2", "S7"]:
        prompt = get_focused_prompt(stage)
        words = len(prompt.split())
        tokens = int(words * 1.7)
        print(f"   {stage}: {len(prompt)} chars, ~{tokens} tokens")
