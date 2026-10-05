from contextlib import AbstractAsyncContextManager
from typing import Protocol

from src.application.agent.conversation.state import ConversationState


class AgentModel(Protocol):

    async def plan(self, context: dict) -> dict: ...

    async def respond(self, context: dict) -> str: ...


class SessionStore(Protocol):

    def get(self, session_id: str) -> ConversationState: ...

    def remove(self, session_id: str) -> None: ...

    def lease(
        self,
        session_id: str,
    ) -> AbstractAsyncContextManager[ConversationState]: ...
