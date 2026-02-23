"""
BSD V2 - Single Agent Coach with Streaming Support
"""

import json
import logging
from typing import Dict, Any, AsyncGenerator

logger = logging.getLogger(__name__)


async def handle_conversation_stream(
    user_message: str,
    state: Dict[str, Any],
    language: str = "he"
) -> AsyncGenerator[str, None]:
    """
    Handle conversation with streaming support.
    
    Yields coach response chunks as they're generated.
    Uses the same handler as non-streaming for consistent prompt/state behavior.
    """
    try:
        # Reuse the full non-streaming path so parsing/safety/state updates stay identical.
        from .single_agent_coach import handle_conversation as non_stream_handler
        coach_message, updated_state = await non_stream_handler(
            user_message=user_message,
            state=state,
            language=language,
        )

        # Stream the final coach message in chunks for SSE UX consistency.
        chunk_size = 80
        for i in range(0, len(coach_message), chunk_size):
            yield coach_message[i:i + chunk_size]
        
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
