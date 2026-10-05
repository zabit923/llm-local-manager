from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

from src.domain.errors.does_not_exists import CustomDoesNotExist
from src.domain.ports.db.commiter import Commiter
from src.domain.ports.db.repositories.catalog_repository import (
    CatalogItem,
    CatalogRepository,
)

CreateSchema = TypeVar("CreateSchema", bound=BaseModel)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)


class CatalogUseCases(Generic[CatalogItem, CreateSchema, UpdateSchema]):

    def __init__(
        self,
        repository: CatalogRepository[CatalogItem],
        commiter: Commiter,
        model: type[CatalogItem],
    ) -> None:
        self._repository = repository
        self._commiter = commiter
        self._model = model

    async def create(self, data: CreateSchema) -> CatalogItem:
        item = self._model(**data.model_dump())
        await self._repository.add(item)
        await self._commiter.commit()
        return item

    async def get(self, item_id: UUID) -> CatalogItem:
        item = await self._repository.get_by_id(item_id)
        if item is None:
            raise CustomDoesNotExist(
                class_name=self._model.__name__,
                model_id=item_id,
            )
        return item

    async def list(self) -> list[CatalogItem]:
        return await self._repository.list_all()

    async def update(self, item_id: UUID, data: UpdateSchema) -> CatalogItem:
        item = await self.get(item_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self._repository.update(item)
        await self._commiter.commit()
        return item

    async def delete(self, item_id: UUID) -> None:
        await self._repository.delete(await self.get(item_id))
        await self._commiter.commit()
