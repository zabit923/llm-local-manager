from sqlalchemy import Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column


class CatalogPricingMixin:

    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
