from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.base import Base

Entity = TypeVar("Entity", bound=Base)


class SqlAlchemyRepository(Generic[Entity]):
    def __init__(self, session: AsyncSession, model: type[Entity]) -> None:
        self._session = session
        self._model = model

    async def add(self, item: Entity) -> Entity:
        return await self._save(item)

    async def update(self, item: Entity) -> Entity:
        return await self._save(item)

    async def _save(self, item: Entity) -> Entity:
        self._session.add(item)
        await self._session.flush()
        return item

    async def get_by_id(self, item_id: UUID) -> Entity | None:
        return await self._session.get(self._model, item_id)

    async def delete(self, item: Entity) -> None:
        await self._session.delete(item)
        await self._session.flush()
