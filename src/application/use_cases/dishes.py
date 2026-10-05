from src.application.schemas.dishes import DishCreate, DishUpdate
from src.application.use_cases.catalog import CatalogUseCases
from src.domain.models.dish import Dish
from src.domain.ports.db.commiter import Commiter
from src.domain.ports.db.repositories.dish_repository import DishRepository


class DishUseCases(CatalogUseCases[Dish, DishCreate, DishUpdate]):

    def __init__(
        self,
        repository: DishRepository,
        commiter: Commiter,
    ) -> None:
        super().__init__(repository, commiter, Dish)
