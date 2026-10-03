"""Disconnecting a browser must not crash the ASGI close handler."""

import asyncio
from contextlib import asynccontextmanager

import pytest
from fastapi import WebSocketDisconnect

from src.presentation.api_v1.views.public import agent


@pytest.mark.asyncio
async def test_browser_disconnect_during_close(monkeypatch):
    class Browser:
        client = "test-browser"

        async def accept(self):
            pass

        async def receive(self):
            return {"type": "websocket.disconnect"}

        async def close(self):
            raise WebSocketDisconnect(code=1006)

    class Remote:
        def __aiter__(self):
            return self

        async def __anext__(self):
            await asyncio.Event().wait()
            raise StopAsyncIteration

    @asynccontextmanager
    async def connect(*_args, **_kwargs):
        yield Remote()

    monkeypatch.setattr(agent.websockets, "connect", connect)
    await asyncio.wait_for(agent.audio_agent(Browser()), timeout=2)
