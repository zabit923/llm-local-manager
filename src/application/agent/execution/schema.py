from pydantic import BaseModel, Field, StrictInt


class ActionProposal(BaseModel):
    name: str = Field(min_length=1)
    sku: str | None = None
    quantity: StrictInt | None = None
    evidence: str | None = None
    branch: str | None = None
    value: str | None = None
