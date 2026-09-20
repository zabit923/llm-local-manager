from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from src.application.schemas.orders import OrderDetail
from src.application.use_cases.orders import OrderUseCases

router = APIRouter(prefix="/orders", tags=["Public orders"], route_class=DishkaRoute)


@router.get("/", response_model=list[OrderDetail])
async def list_orders(use_cases: FromDishka[OrderUseCases]) -> list[OrderDetail]:
    return [OrderDetail.model_validate(order) for order in await use_cases.list_all()]
