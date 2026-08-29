from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr

from src.domain.constants import NAMING_CONVENTION
from src.domain.utils.case_converter import camel_case_to_snake_case


class Base(DeclarativeBase):
    """
    Base model class
    """

    __abstract__ = True

    metadata = MetaData(
        naming_convention=NAMING_CONVENTION,
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"{camel_case_to_snake_case(cls.__name__)}s"

    def __str__(self) -> str:
        return self.__class__.__name__

    def __repr__(self) -> str:
        return str(self)
