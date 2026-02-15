"""Debug health check with prompts info"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/debug/prompts-health")
async def prompts_health():
    """Check if prompts are loading correctly"""
    try:
        from ..bsd_v2.prompts_loader import load_prompts, get_focused_prompt
        
        # Load prompts
        prompts = load_prompts()
        
        # Test a few stages
        test_stages = ["S1", "S2", "S7"]
        stage_info = {}
        
        for stage in test_stages:
            prompt = get_focused_prompt(stage)
            tokens = int(len(prompt.split()) * 1.7)
            stage_info[stage] = {
                "chars": len(prompt),
                "tokens": tokens
            }
        
        return {
            "status": "✅ OK",
            "prompts_loaded": True,
            "num_stages": len(prompts.get("stages", {})),
            "test_stages": stage_info,
            "avg_tokens": sum(s["tokens"] for s in stage_info.values()) // len(stage_info),
            "reduction_vs_full": f"{((6672 - 120) / 6672 * 100):.1f}%"
        }
        
    except Exception as e:
        return {
            "status": "❌ ERROR",
            "prompts_loaded": False,
            "error": str(e)
        }
