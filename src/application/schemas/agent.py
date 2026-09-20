from uuid import UUID

from pydantic import BaseModel, Field


class AgentMessageRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=1000)


class AgentMessageResponse(BaseModel):
    session_id: str
    reply: str
    order_id: UUID | None = None
    cart: list[str] = []
