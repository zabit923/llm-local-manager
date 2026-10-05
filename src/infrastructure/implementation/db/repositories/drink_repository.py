from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.drinks import Drink
from src.domain.ports.db.repositories.drink_repository import DrinkRepository
from src.infrastructure.implementation.db.repositories.base import (
    SqlAlchemyRepository,
)


class SqlAlchemyDrinkRepository(
    SqlAlchemyRepository[Drink],
    DrinkRepository,
):
    """Хранилище напитков каталога."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Drink)

    async def list_all(self) -> list[Drink]:
        result = await self._session.scalars(
            select(Drink).order_by(Drink.name, Drink.volume_ml)
        )
        return list(result)

    async def list_available(self) -> list[Drink]:
        result = await self._session.scalars(
            select(Drink)
            .where(Drink.is_available.is_(True))
            .order_by(Drink.name, Drink.volume_ml)
        )
        return list(result)
