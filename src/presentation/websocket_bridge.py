import asyncio
import os

import websockets
from fastapi import WebSocket, WebSocketDisconnect
from websockets.exceptions import WebSocketException

from src.application.logging import socket_log
from src.presentation.constants import (
    DEFAULT_VOICE_WS_URL,
    MAX_AUDIO_MESSAGE_BYTES,
    VOICE_SERVICE_UNAVAILABLE,
    VOICE_WS_ENV,
)


async def close_socket(socket: WebSocket) -> None:
    try:
        await socket.close()
    except (RuntimeError, WebSocketDisconnect):
        pass


class AudioBridge:
    async def serve(self, socket: WebSocket) -> None:
        await socket.accept()
        socket_log.connected(socket.client)
        url = os.getenv(VOICE_WS_ENV, DEFAULT_VOICE_WS_URL)
        try:
            async with websockets.connect(
                url,
                max_size=MAX_AUDIO_MESSAGE_BYTES,
            ) as remote:
                await self._relay(socket, remote)
        except WebSocketDisconnect:
            pass
        except (OSError, WebSocketException, RuntimeError):
            socket_log.failed(socket.client)
            await self._report_unavailable(socket)
        finally:
            socket_log.disconnected(socket.client)
            await close_socket(socket)

    @staticmethod
    async def _relay(socket: WebSocket, remote) -> None:
        tasks = [
            asyncio.create_task(AudioBridge._upstream(socket, remote)),
            asyncio.create_task(AudioBridge._downstream(socket, remote)),
        ]
        try:
            done, _ = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in done:
                task.result()
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    async def _upstream(socket: WebSocket, remote) -> None:
        while True:
            packet = await socket.receive()
            if packet["type"] == "websocket.disconnect":
                return
            value = packet.get("bytes")
            if value is None:
                value = packet.get("text")
            if value is not None:
                await remote.send(value)

    @staticmethod
    async def _downstream(socket: WebSocket, remote) -> None:
        async for value in remote:
            if isinstance(value, bytes):
                await socket.send_bytes(value)
            else:
                await socket.send_text(value)

    @staticmethod
    async def _report_unavailable(socket: WebSocket) -> None:
        try:
            await socket.send_json(
                {
                    "type": "error",
                    "message": VOICE_SERVICE_UNAVAILABLE,
                }
            )
        except (RuntimeError, WebSocketDisconnect):
            pass
