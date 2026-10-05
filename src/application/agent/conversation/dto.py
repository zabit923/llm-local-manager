from dataclasses import dataclass

from src.application.agent.catalog.dto import CatalogEntry


@dataclass(frozen=True)
class ConversationTurn:

    text: str
    entries: list[CatalogEntry]
    history: list[tuple[str, str]]
    planner_context: dict
