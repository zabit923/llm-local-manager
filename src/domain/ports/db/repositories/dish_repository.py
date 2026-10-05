from typing import Protocol

from src.domain.models.dish import Dish
from src.domain.ports.db.repositories.catalog_repository import (
    CatalogRepository,
)


class DishRepository(CatalogRepository[Dish], Protocol):
    pass
