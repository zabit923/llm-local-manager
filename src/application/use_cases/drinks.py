from src.application.schemas.drinks import DrinkCreate, DrinkUpdate
from src.application.use_cases.catalog import CatalogUseCases
from src.domain.models.drinks import Drink
from src.domain.ports.db.commiter import Commiter
from src.domain.ports.db.repositories.drink_repository import DrinkRepository


class DrinkUseCases(CatalogUseCases[Drink, DrinkCreate, DrinkUpdate]):

    def __init__(
        self,
        repository: DrinkRepository,
        commiter: Commiter,
    ) -> None:
        super().__init__(repository, commiter, Drink)
