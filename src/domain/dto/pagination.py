from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PageParams:
    """
    Параметры пагинации, валидированные на presentation-слое.
    Domain принимает уже корректные значения (offset >= 0, 1 <= limit <= MAX).

    Используется для всех list-методов в Reader-портах.
    """

    offset: int
    limit: int


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    """
    Результат пагинированного запроса.

    items     — текущая страница
    total     — полный count после применения фильтра (для UI "X из Y")
    offset    — отражение запроса (для UI navigation)
    limit     — отражение запроса
    """

    items: list[T]
    total: int
    offset: int
    limit: int

    @property
    def has_next(self) -> bool:
        return self.offset + self.limit < self.total
