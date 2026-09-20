from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.drinks import Drink
from src.domain.ports.db.repositories.drink_repository import DrinkRepository


class SqlAlchemyDrinkRepository(DrinkRepository):
    """Хранилище напитков каталога."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, drink: Drink) -> Drink:
        self._session.add(drink)
        await self._session.flush()
        return drink

    async def update(self, drink: Drink) -> Drink:
        self._session.add(drink)
        await self._session.flush()
        return drink

    async def get_by_id(self, drink_id: UUID) -> Drink | None:
        return await self._session.get(Drink, drink_id)

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

    async def delete(self, drink: Drink) -> None:
        await self._session.delete(drink)
        await self._session.flush()
