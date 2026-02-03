"""
BSD V2 - Single-Agent Conversational Coach

Philosophy: Trust the LLM with clear guidance, not rigid gates.

This is an experimental version that runs side-by-side with V1.
To use V2, set BSD_VERSION=v2 or call /api/chat/v2/message endpoint.
"""

from .single_agent_coach import handle_conversation

__all__ = ["handle_conversation"]
