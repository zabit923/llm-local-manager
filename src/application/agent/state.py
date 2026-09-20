from dataclasses import dataclass, field

from src.application.schemas.orders import OrderItemCreate
from src.domain.models.choises.enum import DeliveryType


@dataclass
class ConversationState:
    items: list[OrderItemCreate] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    branch: str | None = None
    delivery_type: DeliveryType | None = None
    address: str | None = None


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, ConversationState] = {}

    def get(self, session_id: str) -> ConversationState:
        return self._sessions.setdefault(session_id, ConversationState())

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


session_store = InMemorySessionStore()
