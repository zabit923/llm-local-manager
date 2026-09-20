from uuid import UUID

from src.application.schemas.dishes import DishCreate, DishUpdate
from src.domain.errors.does_not_exists import CustomDoesNotExist
from src.domain.models.dish import Dish
from src.domain.ports.db.commiter import Commiter
from src.domain.ports.db.repositories.dish_repository import DishRepository


class DishUseCases:
    def __init__(self, repository: DishRepository, commiter: Commiter) -> None:
        self._repository = repository
        self._commiter = commiter

    async def create(self, data: DishCreate) -> Dish:
        dish = Dish(**data.model_dump())
        await self._repository.add(dish)
        await self._commiter.commit()
        return dish

    async def get(self, dish_id: UUID) -> Dish:
        dish = await self._repository.get_by_id(dish_id)
        if dish is None:
            raise CustomDoesNotExist(class_name="Dish", model_id=dish_id)
        return dish

    async def list(self) -> list[Dish]:
        return await self._repository.list_all()

    async def update(self, dish_id: UUID, data: DishUpdate) -> Dish:
        dish = await self.get(dish_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(dish, field, value)
        await self._repository.update(dish)
        await self._commiter.commit()
        return dish

    async def delete(self, dish_id: UUID) -> None:
        dish = await self.get(dish_id)
        await self._repository.delete(dish)
        await self._commiter.commit()
