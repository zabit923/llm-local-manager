import httpx

from src.application.schemas.agent import AgentMessageResponse
from src.application.voice.constants import AGENT_MESSAGE_PATH


class HttpOrderingAgent:

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def message(self, session_id: str, text: str) -> dict:
        response = await self._client.post(
            AGENT_MESSAGE_PATH,
            json={"session_id": session_id, "text": text},
        )
        response.raise_for_status()
        return AgentMessageResponse.model_validate(
            response.json(),
        ).model_dump(mode="json")
