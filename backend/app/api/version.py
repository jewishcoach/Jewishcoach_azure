"""Simple version check endpoint"""
from fastapi import APIRouter
import os

router = APIRouter()

# Deploy fingerprint: Azure-optimized prompts (minimal JSON, stage-specific gates)
DEPLOY_FINGERPRINT = "azure-optimized-v1"


@router.get("/api/version")
async def get_version():
    """Check which code version is running"""
    prompt_mode = os.getenv("BSD_V2_PROMPT_MODE", "markdown")
    azure_optimized = False
    try:
        from ..bsd_v2.prompts.prompt_manager import assemble_system_prompt
        s1_prompt = assemble_system_prompt("S1", language="he")
        # Azure-optimized: minimal JSON (only topic), stage-specific gate
        azure_optimized = (
            "collected_data" in s1_prompt
            and "Gate (S1→S2)" in s1_prompt
            and "event_description" not in s1_prompt
        )
    except Exception:
        pass

    try:
        from ..bsd_v2.prompts_loader import load_prompts
        prompts_status = "✅ JSON prompts loaded"
        prompts = load_prompts()
        num_stages = len(prompts.get("stages", {}))
    except Exception as e:
        prompts_status = f"❌ JSON prompts failed: {str(e)}"
        num_stages = 0

    json_mode_val = os.getenv("BSD_V2_JSON_MODE", "1").strip().lower()
    json_mode_enabled = json_mode_val in ("1", "true", "yes")

    return {
        "version": "2.0.0",
        "deploy_fingerprint": DEPLOY_FINGERPRINT,
        "prompt_mode": prompt_mode,
        "azure_optimized_prompts": azure_optimized,
        "prompts_system": prompts_status,
        "num_stages": num_stages,
        "json_mode_enabled": json_mode_enabled,
    }
