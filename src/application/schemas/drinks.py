from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.application.schemas.catalog import CatalogUpdate


class DrinkCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    volume_ml: int | None = Field(default=None, gt=0)
    price_minor: int = Field(ge=0)
    is_available: bool = True


class DrinkUpdate(CatalogUpdate):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    volume_ml: int | None = Field(default=None, gt=0)
    price_minor: int | None = Field(default=None, ge=0)
    is_available: bool | None = None


class DrinkDetail(DrinkCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class DrinkList(BaseModel):
    drinks: list[DrinkDetail]
