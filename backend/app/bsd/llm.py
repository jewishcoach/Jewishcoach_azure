from __future__ import annotations

import os
from functools import lru_cache
from typing import Union

from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

"""
LLM configuration for BSD coaching system.

Supports both Azure OpenAI and Google Gemini.
Enterprise-grade: Timeouts, retries, and purpose-specific temperature tuning.
"""


# Temperature mapping per purpose
TEMPERATURE_MAP = {
    "reasoner": 0.1,   # Colder for logical validation (deterministic)
    "talker": 0.35,    # Warmer for empathetic, varied responses (was 0.25)
    "judge": 0.15,     # Cold for quality evaluation
}


@lru_cache(maxsize=8)
def get_azure_chat_llm(*, purpose: str) -> AzureChatOpenAI:
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

    # Check for purpose-specific deployment override
    per_purpose_key = f"AZURE_OPENAI_DEPLOYMENT_NAME_{purpose.upper()}"
    deployment = os.getenv(per_purpose_key, default_deployment)

    # Get temperature for this purpose (default to reasoner temp if unknown)
    temperature = TEMPERATURE_MAP.get(purpose.lower(), 0.1)

    return AzureChatOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
        azure_deployment=deployment,
        temperature=temperature,
        request_timeout=30,  # 30 seconds (enterprise: don't wait forever)
        max_retries=2,       # Retry on transient failures
    )


@lru_cache(maxsize=8)
def get_gemini_chat_llm(*, purpose: str) -> ChatGoogleGenerativeAI:
    """
    Get a Google Gemini LLM client configured for a specific purpose.
    
    Args:
        purpose: One of "reasoner", "talker", "judge"
    
    Returns:
        Configured ChatGoogleGenerativeAI instance
    
    Raises:
        RuntimeError: If Gemini API key is missing
    
    Environment Variables:
        Required:
        - GOOGLE_API_KEY: Google AI API key
        
        Optional:
        - GEMINI_MODEL: Model name (default: gemini-1.5-pro)
    
    Temperature Settings:
        - reasoner: 0.1 (deterministic, logical)
        - talker: 0.35 (creative, empathetic, varied)
        - judge: 0.15 (consistent evaluation)
    """
    # Load configuration
    api_key = os.getenv("GOOGLE_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Validate required config
    if not api_key:
        raise RuntimeError(
            "Missing Google AI configuration. "
            "Set GOOGLE_API_KEY environment variable."
        )
    
    # Get temperature for this purpose
    temperature = TEMPERATURE_MAP.get(purpose.lower(), 0.1)
    
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=temperature,
        request_timeout=30,
        max_retries=2,
    )


def get_chat_llm(*, purpose: str) -> Union[AzureChatOpenAI, ChatGoogleGenerativeAI]:
    """
    Get an LLM client configured for a specific purpose.
    
    Automatically selects between Azure OpenAI and Gemini based on:
    - LLM_PROVIDER environment variable ("azure" or "gemini")
    - Defaults to Azure if not specified
    
    Args:
        purpose: One of "reasoner", "talker", "judge"
    
    Returns:
        Configured LLM instance (Azure or Gemini)
    
    Examples:
        >>> llm = get_chat_llm(purpose="talker")
        >>> # Returns Azure or Gemini based on LLM_PROVIDER
    """
    provider = os.getenv("LLM_PROVIDER", "azure").lower()
    
    if provider == "gemini":
        return get_gemini_chat_llm(purpose=purpose)
    else:
        return get_azure_chat_llm(purpose=purpose)


# Public API
__all__ = ["get_azure_chat_llm", "get_gemini_chat_llm", "get_chat_llm"]
