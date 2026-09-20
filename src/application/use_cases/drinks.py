from uuid import UUID

from src.application.schemas.drinks import DrinkCreate, DrinkUpdate
from src.domain.errors.does_not_exists import CustomDoesNotExist
from src.domain.models.drinks import Drink
from src.domain.ports.db.commiter import Commiter
from src.domain.ports.db.repositories.drink_repository import DrinkRepository


class DrinkUseCases:
    def __init__(self, repository: DrinkRepository, commiter: Commiter) -> None:
        self._repository = repository
        self._commiter = commiter

    async def create(self, data: DrinkCreate) -> Drink:
        drink = Drink(**data.model_dump())
        await self._repository.add(drink)
        await self._commiter.commit()
        return drink

    async def get(self, drink_id: UUID) -> Drink:
        drink = await self._repository.get_by_id(drink_id)
        if drink is None:
            raise CustomDoesNotExist(class_name="Drink", model_id=drink_id)
        return drink

    async def list(self) -> list[Drink]:
        return await self._repository.list_all()

    async def update(self, drink_id: UUID, data: DrinkUpdate) -> Drink:
        drink = await self.get(drink_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(drink, field, value)
        await self._repository.update(drink)
        await self._commiter.commit()
        return drink

    async def delete(self, drink_id: UUID) -> None:
        drink = await self.get(drink_id)
        await self._repository.delete(drink)
        await self._commiter.commit()
