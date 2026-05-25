"""Tests for Azure content-filter detection and user-facing fallback."""

from __future__ import annotations

import pytest

from app.azure_openai_content_filter import (
    ContentFilterBlockedError,
    content_filter_user_message,
    invoke_structured_coach_llm,
    is_content_filter_error,
)


@pytest.mark.parametrize(
    "msg",
    [
        "The response was filtered due to the prompt triggering Azure OpenAI's content management policy",
        "Error code: 400 - content_filter",
        "ResponsibleAIPolicyViolation",
    ],
)
def test_is_content_filter_error_detects_azure_markers(msg: str):
    assert is_content_filter_error(RuntimeError(msg)) is True


def test_is_content_filter_error_ignores_unrelated():
    assert is_content_filter_error(RuntimeError("connection timeout")) is False


def test_content_filter_user_message_bilingual():
    assert "מגבלה" in content_filter_user_message("he")
    assert "safety limit" in content_filter_user_message("en").lower()


@pytest.mark.asyncio
async def test_invoke_structured_coach_llm_retries_then_raises_content_filter():
    class FakeLLM:
        def __init__(self):
            self.calls = 0

        async def ainvoke(self, _messages):
            self.calls += 1
            raise RuntimeError("content management policy triggered")

    llm = FakeLLM()
    with pytest.raises(ContentFilterBlockedError):
        await invoke_structured_coach_llm(
            llm,
            [],
            context="x" * 3000,
            system_prompt="coach",
            language="he",
        )
    assert llm.calls == 2


@pytest.mark.asyncio
async def test_invoke_structured_coach_llm_succeeds_on_retry():
    class FakeLLM:
        def __init__(self):
            self.calls = 0

        async def ainvoke(self, _messages):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("content_filter")
            return {"parsed": None, "raw": None}

    llm = FakeLLM()
    result = await invoke_structured_coach_llm(
        llm,
        [],
        context="hello",
        system_prompt="coach",
        language="en",
    )
    assert result == {"parsed": None, "raw": None}
    assert llm.calls == 2
