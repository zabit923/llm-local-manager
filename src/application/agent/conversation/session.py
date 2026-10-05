import asyncio
from dataclasses import dataclass, field

from src.application.agent.conversation.state import ConversationState


@dataclass
class _Session:
    state: ConversationState = field(default_factory=ConversationState)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    leases: int = 0
    discard: bool = False
