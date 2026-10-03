"""Malformed inference responses become controlled model failures."""

import httpx
import pytest

from src.application.agent.llm import ModelUnavailable, QwenAgentModel


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [
    b"not-json",
    b'{"choices":[{"message":{"content":null}}]}',
    b'{"choices":[{"message":{"content":[]}}]}',
    b'{"choices":[{"message":{"content":" "}}]}',
    b'{"choices":[]}',
])
async def test_invalid_llm_content_is_controlled(monkeypatch, body):
    original_client = httpx.AsyncClient
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=body),
    )
    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda **kwargs: original_client(**kwargs, transport=transport),
    )
    model = QwenAgentModel()
    with pytest.raises(ModelUnavailable):
        await model._chat([], "reply", temperature=0.55, max_tokens=220)
