from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.models.order import OrderItem
from src.domain.ports.db.repositories.order_item_repository import (
    OrderItemRepository,
)


class SqlAlchemyOrderItemRepository(OrderItemRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _with_menu_item(statement):
        return statement.options(
            selectinload(OrderItem.dish),
            selectinload(OrderItem.drink),
        )

    async def add(self, item: OrderItem) -> OrderItem:
        self._session.add(item)
        await self._session.flush()
        return item

    async def update(self, item: OrderItem) -> OrderItem:
        self._session.add(item)
        await self._session.flush()
        return item

    async def get_by_id(self, item_id: UUID) -> OrderItem | None:
        statement = self._with_menu_item(
            select(OrderItem).where(OrderItem.id == item_id)
        )
        return await self._session.scalar(statement)

    async def list_by_order_id(self, order_id: UUID) -> list[OrderItem]:
        statement = self._with_menu_item(
            select(OrderItem)
            .where(OrderItem.order_id == order_id)
            .order_by(OrderItem.created_at)
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def delete(self, item: OrderItem) -> None:
        await self._session.delete(item)
        await self._session.flush()
