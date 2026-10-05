from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.dish import Dish
from src.domain.ports.db.repositories.dish_repository import DishRepository
from src.infrastructure.implementation.db.repositories.base import (
    SqlAlchemyRepository,
)


class SqlAlchemyDishRepository(
    SqlAlchemyRepository[Dish],
    DishRepository,
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Dish)

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
