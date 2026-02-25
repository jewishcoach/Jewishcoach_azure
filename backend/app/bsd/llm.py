from __future__ import annotations

import os
from functools import lru_cache

from langchain_openai import AzureChatOpenAI

"""
LLM configuration for BSD coaching system.

Supports both Azure OpenAI and Google Gemini.
Enterprise-grade: Timeouts, retries, and purpose-specific temperature tuning.
"""


# Temperature mapping per purpose
# talker: 0.2 max for JSON/Structured Output stability (0.35 caused free text before JSON)
TEMPERATURE_MAP = {
    "reasoner": 0.1,   # Colder for logical validation (deterministic)
    "talker": 0.2,     # Low for JSON stability; still natural for coaching
    "judge": 0.15,     # Cold for quality evaluation
}


def _build_azure_llm(*, deployment: str, temperature: float = 0.2) -> AzureChatOpenAI:
    """Build Azure LLM with given deployment (for A/B test)."""
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    timeout_seconds = int(os.getenv("AZURE_OPENAI_TIMEOUT_SECONDS", "90"))
    max_retries = int(os.getenv("AZURE_OPENAI_MAX_RETRIES", "2"))
    if not api_key or not endpoint:
        raise RuntimeError("Missing Azure OpenAI configuration.")
    return AzureChatOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
        azure_deployment=deployment,
        temperature=temperature,
        request_timeout=timeout_seconds,
        max_retries=max_retries,
    )


@lru_cache(maxsize=8)
def get_azure_chat_llm(*, purpose: str, deployment: str | None = None) -> AzureChatOpenAI:
    """
    Get an Azure OpenAI LLM client configured for a specific purpose.
    
    Args:
        purpose: One of "reasoner", "talker", "judge"
    
    Returns:
        Configured AzureChatOpenAI instance
    
    Raises:
        RuntimeError: If Azure OpenAI credentials are missing
    
    Environment Variables:
        Required:
        - AZURE_OPENAI_API_KEY: Azure OpenAI API key
        - AZURE_OPENAI_ENDPOINT: Azure endpoint URL
        
        Optional:
        - AZURE_OPENAI_API_VERSION: API version (default: 2024-08-01-preview)
        - AZURE_OPENAI_DEPLOYMENT_NAME: Default deployment (default: gpt-4o)
        - AZURE_OPENAI_DEPLOYMENT_NAME_REASONER: Override for reasoner
        - AZURE_OPENAI_DEPLOYMENT_NAME_TALKER: Override for talker
        - AZURE_OPENAI_DEPLOYMENT_NAME_JUDGE: Override for judge
    
    Temperature Settings:
        - reasoner: 0.1 (deterministic, logical)
        - talker: 0.35 (creative, empathetic, varied)
        - judge: 0.15 (consistent evaluation)
    
    Examples:
        >>> llm = get_azure_chat_llm(purpose="talker")
        >>> llm.temperature
        0.35
    """
    # Load configuration
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    default_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

    # Validate required config
    if not api_key or not endpoint:
        raise RuntimeError(
            "Missing Azure OpenAI configuration. "
            "Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT."
        )

    # Explicit deployment override (e.g. for A/B test)
    if deployment:
        deployment_name = deployment
    else:
        per_purpose_key = f"AZURE_OPENAI_DEPLOYMENT_NAME_{purpose.upper()}"
        deployment_name = os.getenv(per_purpose_key, default_deployment)

    # Get temperature for this purpose (default to reasoner temp if unknown)
    temperature = TEMPERATURE_MAP.get(purpose.lower(), 0.1)

    # 90s default: Azure can take 45-60s under load; 30s caused premature timeouts
    timeout_seconds = int(os.getenv("AZURE_OPENAI_TIMEOUT_SECONDS", "90"))
    max_retries = int(os.getenv("AZURE_OPENAI_MAX_RETRIES", "2"))  # Retry on 429 throttling

    return AzureChatOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
        azure_deployment=deployment_name,
        temperature=temperature,
        request_timeout=timeout_seconds,
        max_retries=max_retries,
    )


@lru_cache(maxsize=1)
def get_azure_chat_llm_4o_mini() -> AzureChatOpenAI:
    """Get Azure LLM for gpt-4o-mini (A/B test variant)."""
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME_4O_MINI", "gpt-4o-mini")
    return _build_azure_llm(deployment=deployment, temperature=0.2)


# Google Gemini support removed - Azure OpenAI only
# @lru_cache(maxsize=8)
# def get_gemini_chat_llm(*, purpose: str) -> ChatGoogleGenerativeAI:
#     ...


def get_chat_llm(*, purpose: str) -> AzureChatOpenAI:
    """
    Get an LLM client configured for a specific purpose.
    
    Uses Azure OpenAI only.
    
    Args:
        purpose: One of "reasoner", "talker", "judge"
    
    Returns:
        Configured Azure OpenAI LLM instance
    
    Examples:
        >>> llm = get_chat_llm(purpose="talker")
    """
    return get_azure_chat_llm(purpose=purpose)


# Public API
__all__ = ["get_azure_chat_llm", "get_chat_llm", "get_azure_chat_llm_4o_mini"]
