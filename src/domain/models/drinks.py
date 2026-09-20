from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.models.base import Base
from src.domain.models.mixins.id_int_pk import UUIDPkMixin
from src.domain.models.mixins.timestamp import TimestampMixin

if TYPE_CHECKING:
    from src.domain.models.order import OrderItem


class Drink(Base, UUIDPkMixin, TimestampMixin):
    """Напиток из меню."""

    __table_args__ = (
        CheckConstraint("price_minor >= 0", name="price_minor_non_negative"),
        CheckConstraint(
            "volume_ml IS NULL OR volume_ml > 0", name="volume_positive"
        ),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    volume_ml: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    order_items: Mapped[list[OrderItem]] = relationship(back_populates="drink")
