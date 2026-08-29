from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.models.base import Base
from src.domain.models.mixins.id_int_pk import UUIDPkMixin
from src.domain.models.mixins.timestamp import TimestampMixin

if TYPE_CHECKING:
    from src.domain.models.order import OrderItem


class Dish(Base, UUIDPkMixin, TimestampMixin):
    """Позиция основного меню, например пицца или закуска."""

    __tablename__ = "dishes"
    __table_args__ = (
        CheckConstraint("price_minor >= 0", name="price_minor_non_negative"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    order_items: Mapped[list[OrderItem]] = relationship(back_populates="dish")
