from dataclasses import dataclass

from src.domain.models.order import Order


@dataclass(frozen=True)
class ReplyFacts:

    reply: str
    order: Order | None
    events: list[dict]
    history: list[tuple[str, str]]
    context: dict

    @property
    def lowered(self) -> str:
        return self.reply.lower()

    @property
    def added(self) -> bool:
        return any(
            event.get("action") == "add_item"
            and event.get("status") == "applied"
            for event in self.events
        )
