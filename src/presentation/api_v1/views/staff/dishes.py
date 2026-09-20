from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status

from src.application.schemas.dishes import DishCreate, DishDetail, DishList, DishUpdate
from src.application.use_cases.dishes import DishUseCases


router = APIRouter(
    prefix="/dishes",
    tags=["Staff dishes"],
    route_class=DishkaRoute,
)


@router.post("/", response_model=DishDetail, status_code=status.HTTP_201_CREATED)
async def create_dish(
    data: DishCreate,
    use_cases: FromDishka[DishUseCases],
) -> DishDetail:
    return DishDetail.model_validate(await use_cases.create(data))


@router.get("/", response_model=DishList)
async def list_dishes(use_cases: FromDishka[DishUseCases]) -> DishList:
    dishes = await use_cases.list()
    return DishList(dishes=[DishDetail.model_validate(dish) for dish in dishes])


@router.get("/{dish_id}", response_model=DishDetail)
async def get_dish(
    dish_id: UUID,
    use_cases: FromDishka[DishUseCases],
) -> DishDetail:
    return DishDetail.model_validate(await use_cases.get(dish_id))


@router.patch("/{dish_id}", response_model=DishDetail)
async def update_dish(
    dish_id: UUID,
    data: DishUpdate,
    use_cases: FromDishka[DishUseCases],
) -> DishDetail:
    return DishDetail.model_validate(await use_cases.update(dish_id, data))


@router.delete("/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dish(
    dish_id: UUID,
    use_cases: FromDishka[DishUseCases],
) -> Response:
    await use_cases.delete(dish_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
