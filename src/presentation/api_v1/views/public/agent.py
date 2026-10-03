import asyncio
import os

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import httpx
import websockets

from src.application.schemas.agent import (
    AgentMessageRequest,
    AgentMessageResponse,
)
from src.application.logging import socket_log
from src.application.services.order_agent import OrderAgent


router = APIRouter(prefix="/agent", tags=["Agent"], route_class=DishkaRoute)


@router.websocket("/audio")
async def audio_agent(websocket: WebSocket) -> None:
    """Relay binary PCM and voice events to the local model gateway."""
    await websocket.accept()
    socket_log.connected(websocket.client)
    tasks = []
    try:
        url = os.getenv(
            "VOICE_WS_URL", "ws://host.docker.internal:8001/ws"
        )
        async with websockets.connect(url, max_size=8 * 1024 * 1024) as remote:
            async def upstream():
                while True:
                    packet = await websocket.receive()
                    if packet["type"] == "websocket.disconnect":
                        return
                    value = packet.get("bytes")
                    if value is None:
                        value = packet.get("text")
                    if value is not None:
                        await remote.send(value)

            async def downstream():
                async for value in remote:
                    if isinstance(value, bytes):
                        await websocket.send_bytes(value)
                    else:
                        await websocket.send_text(value)

            tasks = [
                asyncio.create_task(upstream()),
                asyncio.create_task(downstream()),
            ]
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in tasks:
                if task.done():
                    task.result()
    except WebSocketDisconnect:
        pass
    except Exception:
        socket_log.failed(websocket.client)
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Голосовой сервис недоступен. Попробуйте позже.",
            })
        except (RuntimeError, WebSocketDisconnect):
            pass
    finally:
        socket_log.disconnected(websocket.client)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        try:
            await websocket.close()
        except (RuntimeError, WebSocketDisconnect):
            pass


@router.post("/message", response_model=AgentMessageResponse)
async def message(
    data: AgentMessageRequest,
    agent: FromDishka[OrderAgent],
) -> AgentMessageResponse:
    return await agent.handle(data.session_id, data.text)


@router.websocket("/ws")
async def websocket_agent(
    websocket: WebSocket,
) -> None:
    await websocket.accept()
    socket_log.connected(websocket.client)
    try:
        while True:
            data = await websocket.receive_json()
            socket_log.received(data)
            async with httpx.AsyncClient(
                base_url="http://127.0.0.1:8888", timeout=30.0
            ) as client:
                response = await client.post(
                    "/api/v1/pub/agent/message", json=data
                )
                response.raise_for_status()
                payload = response.json()
                await websocket.send_json(payload)
                socket_log.sent(payload)
    except WebSocketDisconnect:
        socket_log.disconnected(websocket.client)
        return
    except Exception:
        socket_log.failed(websocket.client)
        raise
