from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.models.order import OrderItem
from src.domain.ports.db.repositories.order_item_repository import (
    OrderItemRepository,
)
from src.infrastructure.implementation.db.repositories.base import (
    SqlAlchemyRepository,
)


class SqlAlchemyOrderItemRepository(
    SqlAlchemyRepository[OrderItem],
    OrderItemRepository,
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrderItem)

    @staticmethod
    def _with_menu_item(statement):
        return statement.options(
            selectinload(OrderItem.dish),
            selectinload(OrderItem.drink),
        )

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
