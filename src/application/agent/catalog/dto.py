from dataclasses import dataclass

from src.domain.models.dish import Dish
from src.domain.models.drinks import Drink

MenuItem = Dish | Drink


@dataclass(frozen=True)
class CatalogMatch:
    item: MenuItem
    kind: str


@dataclass(frozen=True)
class CatalogEntry:
    sku: str
    item: MenuItem
    kind: str

    def as_context(self) -> dict[str, object]:
        return {
            "sku": self.sku,
            "name": self.item.name,
            "price_minor": self.item.price_minor,
            "available": self.item.is_available,
        }
