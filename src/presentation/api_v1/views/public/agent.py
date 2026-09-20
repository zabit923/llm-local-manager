from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import httpx

from src.application.schemas.agent import AgentMessageRequest, AgentMessageResponse
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
    try:
        while True:
            data = await websocket.receive_json()
            async with httpx.AsyncClient(base_url="http://127.0.0.1:8888", timeout=30.0) as client:
                response = await client.post("/api/v1/pub/agent/message", json=data)
                response.raise_for_status()
                await websocket.send_json(response.json())
    except WebSocketDisconnect:
        return
