from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DishCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    price_minor: int = Field(ge=0)
    is_available: bool = True


class DishUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    price_minor: int | None = Field(default=None, ge=0)
    is_available: bool | None = None


class DishDetail(DishCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class DishList(BaseModel):
    dishes: list[DishDetail]
