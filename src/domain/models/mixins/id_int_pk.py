from sqlalchemy import BigInteger, Identity
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)
from uuid6 import UUID, uuid7


class IdBigIntPkMixin:
    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )


class UUIDPkMixin:
    id: Mapped[UUID] = mapped_column(
        type_=PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
        nullable=False,
    )
