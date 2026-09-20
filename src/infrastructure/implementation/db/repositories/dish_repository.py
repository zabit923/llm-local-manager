from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.dish import Dish
from src.domain.ports.db.repositories.dish_repository import DishRepository


class SqlAlchemyDishRepository(DishRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, dish: Dish) -> Dish:
        self._session.add(dish)
        await self._session.flush()
        return dish

    async def update(self, dish: Dish) -> Dish:
        self._session.add(dish)
        await self._session.flush()
        return dish

    async def get_by_id(self, dish_id: UUID) -> Dish | None:
        return await self._session.get(Dish, dish_id)

    async def list_all(self) -> list[Dish]:
        result = await self._session.scalars(select(Dish).order_by(Dish.name))
        return list(result)

    async def list_available(self) -> list[Dish]:
        result = await self._session.scalars(
            select(Dish)
            .where(Dish.is_available.is_(True))
            .order_by(Dish.created_at)
        )
        return list(result)

    async def delete(self, dish: Dish) -> None:
        await self._session.delete(dish)
        await self._session.flush()
