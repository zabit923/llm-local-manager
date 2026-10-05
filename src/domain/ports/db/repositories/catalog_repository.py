from typing import Protocol, TypeVar
from uuid import UUID

from src.domain.models.dish import Dish
from src.domain.models.drinks import Drink

CatalogItem = TypeVar("CatalogItem", Dish, Drink)


class CatalogRepository(Protocol[CatalogItem]):

    async def add(self, item: CatalogItem) -> CatalogItem: ...

    async def update(self, item: CatalogItem) -> CatalogItem: ...

    async def get_by_id(self, item_id: UUID) -> CatalogItem | None: ...

    async def list_all(self) -> list[CatalogItem]: ...

    async def list_available(self) -> list[CatalogItem]: ...

    async def delete(self, item: CatalogItem) -> None: ...
