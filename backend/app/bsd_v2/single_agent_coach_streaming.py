"""
BSD V2 - Single Agent Coach with Streaming Support
"""

import json
import logging
from typing import Dict, Any, AsyncGenerator
from langchain_core.messages import SystemMessage, HumanMessage

from ..bsd.llm import get_azure_chat_llm
from .state_schema_v2 import add_message, get_conversation_history
from .prompt_optimized import SYSTEM_PROMPT_OPTIMIZED_HE, SYSTEM_PROMPT_OPTIMIZED_EN

logger = logging.getLogger(__name__)


async def handle_conversation_stream(
    user_message: str,
    state: Dict[str, Any],
    language: str = "he"
) -> AsyncGenerator[str, None]:
    """
    Handle conversation with streaming support.
    
    Yields coach response chunks as they're generated.
    """
    try:
        # Select prompt based on language
        system_prompt = SYSTEM_PROMPT_OPTIMIZED_HE if language == "he" else SYSTEM_PROMPT_OPTIMIZED_EN
        
        # Get LLM with streaming enabled
        llm = get_azure_chat_llm(purpose="talker")
        
        # Build conversation history
        history = get_conversation_history(state)
        messages = [
            SystemMessage(content=system_prompt),
            *history,
            HumanMessage(content=user_message)
        ]
        
        # Stream response
        full_response = ""
        async for chunk in llm.astream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                full_response += chunk.content
                yield chunk.content
        
        # Update state with full response
        updated_state = add_message(
            state=state,
            role="user",
            content=user_message
        )
        
        updated_state = add_message(
            state=updated_state,
            role="assistant",
            content=full_response
        )
        
        # Yield final state as JSON (marked with special prefix)
        yield f"\n__STATE_UPDATE__:{json.dumps(updated_state)}"
        
    except Exception as e:
        logger.error(f"Error in streaming conversation: {e}")
        yield f"\n__ERROR__:{str(e)}"


# Also keep non-streaming version for compatibility
def handle_conversation(
    user_message: str,
    state: Dict[str, Any],
    language: str = "he"
) -> tuple[str, Dict[str, Any]]:
    """
    Handle conversation without streaming (original function).
    """
    from .single_agent_coach import handle_conversation as original_handler
    return original_handler(user_message, state, language)


__all__ = ["handle_conversation_stream", "handle_conversation"]
