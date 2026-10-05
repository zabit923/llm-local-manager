from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status

from src.application.schemas.drinks import (
    DrinkCreate,
    DrinkDetail,
    DrinkList,
    DrinkUpdate,
)
from src.application.use_cases.drinks import DrinkUseCases

router = APIRouter(
    prefix="/drinks",
    tags=["Staff drinks"],
    route_class=DishkaRoute,
)


@router.post(
    "/", response_model=DrinkDetail, status_code=status.HTTP_201_CREATED
)
async def create_drink(
    data: DrinkCreate,
    use_cases: FromDishka[DrinkUseCases],
) -> DrinkDetail:
    return DrinkDetail.model_validate(await use_cases.create(data))


@router.get("/", response_model=DrinkList)
async def list_drinks(use_cases: FromDishka[DrinkUseCases]) -> DrinkList:
    drinks = await use_cases.list()
    return DrinkList(
        drinks=[DrinkDetail.model_validate(drink) for drink in drinks]
    )


@router.get("/{drink_id}", response_model=DrinkDetail)
async def get_drink(
    drink_id: UUID,
    use_cases: FromDishka[DrinkUseCases],
) -> DrinkDetail:
    return DrinkDetail.model_validate(await use_cases.get(drink_id))


@router.patch("/{drink_id}", response_model=DrinkDetail)
async def update_drink(
    drink_id: UUID,
    data: DrinkUpdate,
    use_cases: FromDishka[DrinkUseCases],
) -> DrinkDetail:
    return DrinkDetail.model_validate(await use_cases.update(drink_id, data))


@router.delete("/{drink_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_drink(
    drink_id: UUID,
    use_cases: FromDishka[DrinkUseCases],
) -> Response:
    await use_cases.delete(drink_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
