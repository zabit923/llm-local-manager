from dataclasses import dataclass, field
from uuid import UUID

from src.application.schemas.orders import OrderItemCreate
from src.domain.models.choises.enum import DeliveryType


@dataclass
class CartLine:
    item_id: UUID
    kind: str
    name: str
    unit_price_minor: int
    quantity: int

    @property
    def label(self) -> str:
        return f"{self.quantity} {self.name}"

    def to_order_item(self) -> OrderItemCreate:
        field = "dish_id" if self.kind == "dish" else "drink_id"
        return OrderItemCreate(
            **{field: self.item_id, "quantity": self.quantity}
        )


@dataclass
class ConversationState:
    lines: list[CartLine] = field(default_factory=list)
    branch: str | None = None
    delivery_type: DeliveryType | None = None
    address: str | None = None
    address_street: str | None = None
    suggested_delivery: DeliveryType | None = None
    pending_item_text: str | None = None
    history: list[tuple[str, str]] = field(default_factory=list)

    @property
    def items(self) -> list[OrderItemCreate]:
        return [line.to_order_item() for line in self.lines]

    @property
    def labels(self) -> list[str]:
        return [line.label for line in self.lines]

    @property
    def subtotal_minor(self) -> int:
        return sum(line.unit_price_minor * line.quantity for line in self.lines)


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, ConversationState] = {}

    def get(self, session_id: str) -> ConversationState:
        return self._sessions.setdefault(session_id, ConversationState())

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


session_store = InMemorySessionStore()
