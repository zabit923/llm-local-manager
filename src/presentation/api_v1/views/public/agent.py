from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import httpx

from src.application.schemas.agent import (
    AgentMessageRequest,
    AgentMessageResponse,
)
from src.application.logging import socket_log
from src.application.services.order_agent import OrderAgent


router = APIRouter(prefix="/agent", tags=["Agent"], route_class=DishkaRoute)


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
