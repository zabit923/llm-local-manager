from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.models.order import Order, OrderItem
from src.domain.ports.db.repositories.order_repository import OrderRepository


class SqlAlchemyOrderRepository(OrderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _with_items(statement):
        return statement.options(
            selectinload(Order.items).selectinload(OrderItem.dish),
            selectinload(Order.items).selectinload(OrderItem.drink),
        )

    async def add(self, order: Order) -> Order:
        self._session.add(order)
        await self._session.flush()
        return order

    async def update(self, order: Order) -> Order:
        self._session.add(order)
        await self._session.flush()
        return order

    async def get_by_id(self, order_id: UUID) -> Order | None:
        statement = self._with_items(select(Order).where(Order.id == order_id))
        return await self._session.scalar(statement)

    async def get_by_id_for_update(self, order_id: UUID) -> Order | None:
        statement = self._with_items(
            select(Order).where(Order.id == order_id).with_for_update()
        )
        return await self._session.scalar(statement)

    async def list_all(self) -> list[Order]:
        statement = self._with_items(
            select(Order).order_by(Order.created_at.desc())
        )
        result = await self._session.scalars(statement)
        return list(result)
