from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from src.application.agent.conversation.session import _Session
from src.application.agent.conversation.state import ConversationState


class InMemorySessionStore:

    def __init__(self) -> None:
        self._sessions: dict[str, _Session] = {}

    def get(self, session_id: str) -> ConversationState:
        return self._entry(session_id).state

    def _entry(self, session_id: str) -> _Session:
        entry = self._sessions.get(session_id)
        if entry is None:
            entry = _Session()
            self._sessions[session_id] = entry
        return entry

    def remove(self, session_id: str) -> None:
        entry = self._sessions.get(session_id)
        if entry is None:
            return
        if entry.leases:
            entry.state = ConversationState()
            entry.discard = True
        else:
            self._sessions.pop(session_id, None)

    @asynccontextmanager
    async def lease(self, session_id: str) -> AsyncIterator[ConversationState]:
        entry = self._entry(session_id)
        entry.leases += 1
        try:
            async with entry.lock:
                entry.discard = False
                yield entry.state
        finally:
            entry.leases -= 1
            if entry.discard and entry.leases == 0:
                self._sessions.pop(session_id, None)
