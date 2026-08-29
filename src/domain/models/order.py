from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum as SqlEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import UUID

from src.domain.models.base import Base
from src.domain.models.choises.enum import DeliveryType, OrderStatus, PaymentMethod
from src.domain.models.mixins.id_int_pk import UUIDPkMixin
from src.domain.models.mixins.timestamp import TimestampMixin

if TYPE_CHECKING:
    from src.domain.models.dish import Dish
    from src.domain.models.drinks import Drink


class Order(Base, UUIDPkMixin, TimestampMixin):
    """Заказ клиента и его состояние."""

    status: Mapped[OrderStatus] = mapped_column(
        SqlEnum(OrderStatus, name="order_status"),
        nullable=False,
        default=OrderStatus.pending,
        server_default=OrderStatus.pending.value,
    )
    customer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    delivery_type: Mapped[DeliveryType] = mapped_column(
        SqlEnum(DeliveryType, name="delivery_type"),
        nullable=False,
        default=DeliveryType.delivery,
        server_default=DeliveryType.delivery.value,
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        SqlEnum(PaymentMethod, name="payment_method"),
        nullable=False,
        default=PaymentMethod.cash,
        server_default=PaymentMethod.cash.value,
    )
    total_price_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderItem(Base, UUIDPkMixin, TimestampMixin):
    """Строка заказа с неизменяемым названием и ценой на момент покупки."""

    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price_minor >= 0", name="unit_price_minor_non_negative"),
        CheckConstraint(
            "(dish_id IS NOT NULL AND drink_id IS NULL) "
            "OR (dish_id IS NULL AND drink_id IS NOT NULL)",
            name="exactly_one_menu_item",
        ),
    )

    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dish_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("dishes.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    drink_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("drinks.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    dish: Mapped[Dish | None] = relationship(back_populates="order_items")
    drink: Mapped[Drink | None] = relationship(back_populates="order_items")
