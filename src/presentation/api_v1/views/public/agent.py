from json import JSONDecodeError

from dishka import Scope
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from src.application.agent.service import OrderAgent
from src.application.logging import socket_log
from src.application.schemas.agent import (
    AgentMessageRequest,
    AgentMessageResponse,
)
from src.presentation.constants import INVALID_AGENT_MESSAGE
from src.presentation.websocket_bridge import AudioBridge, close_socket

router = APIRouter(
    prefix="/agent",
    tags=["Agent"],
    route_class=DishkaRoute,
)


@router.websocket("/audio")
async def audio_agent(websocket: WebSocket) -> None:
    await AudioBridge().serve(websocket)


@router.post("/message", response_model=AgentMessageResponse)
async def message(
    data: AgentMessageRequest,
    agent: FromDishka[OrderAgent],
) -> AgentMessageResponse:
    return await agent.handle(data.session_id, data.text)


@router.websocket("/ws")
async def websocket_agent(websocket: WebSocket) -> None:
    await websocket.accept()
    socket_log.connected(websocket.client)
    try:
        while True:
            try:
                data = AgentMessageRequest.model_validate(
                    await websocket.receive_json(),
                )
            except (JSONDecodeError, ValidationError):
                await websocket.send_json(
                    {"type": "error", "message": INVALID_AGENT_MESSAGE}
                )
                continue
            socket_log.received(data.model_dump())
            container = websocket.state.dishka_container
            async with container(scope=Scope.REQUEST) as request_container:
                agent = await request_container.get(OrderAgent)
                response = await agent.handle(data.session_id, data.text)
            payload = response.model_dump(mode="json")
            await websocket.send_json(payload)
            socket_log.sent(payload)
    except WebSocketDisconnect:
        pass
    finally:
        socket_log.disconnected(websocket.client)
        await close_socket(websocket)
