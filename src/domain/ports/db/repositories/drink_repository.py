from typing import Protocol

from src.domain.models.drinks import Drink
from src.domain.ports.db.repositories.catalog_repository import (
    CatalogRepository,
)


class DrinkRepository(CatalogRepository[Drink], Protocol):
    pass
