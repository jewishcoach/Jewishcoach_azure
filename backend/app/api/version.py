"""Simple version check endpoint"""
from fastapi import APIRouter
import os

router = APIRouter()

@router.get("/api/version")
async def get_version():
    """Check which code version is running"""
    try:
        # Try to load new prompts
        from ..bsd_v2.prompts_loader import load_prompts
        prompts_status = "✅ JSON prompts loaded"
        
        prompts = load_prompts()
        num_stages = len(prompts.get("stages", {}))
    except Exception as e:
        prompts_status = f"❌ JSON prompts failed: {str(e)}"
        num_stages = 0
    
    return {
        "version": "2.0.0",
        "commit": "bffadaa",
        "prompts_system": prompts_status,
        "num_stages": num_stages,
        "expected_tokens": "~305 per stage"
    }
