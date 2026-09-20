from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, status

from src.application.schemas.orders import (
    OrderCreate,
    OrderDetail,
    OrderItemQuantityUpdate,
)
from src.application.use_cases.orders import OrderUseCases


router = APIRouter(
    prefix="/orders",
    tags=["Staff orders"],
    route_class=DishkaRoute,
)


@router.post("/", response_model=OrderDetail, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    use_cases: FromDishka[OrderUseCases],
) -> OrderDetail:
    return OrderDetail.model_validate(await use_cases.create(data))


@router.get("/{order_id}", response_model=OrderDetail)
async def get_order(
    order_id: UUID,
    use_cases: FromDishka[OrderUseCases],
) -> OrderDetail:
    return OrderDetail.model_validate(await use_cases.get(order_id))


@router.get("/", response_model=list[OrderDetail])
async def list_orders(use_cases: FromDishka[OrderUseCases]) -> list[OrderDetail]:
    return [OrderDetail.model_validate(order) for order in await use_cases.list_all()]


@router.post("/{order_id}/dishes/{dish_id}", response_model=OrderDetail)
async def add_dish(
    order_id: UUID,
    dish_id: UUID,
    quantity: Annotated[int, Query(gt=0)],
    use_cases: FromDishka[OrderUseCases],
) -> OrderDetail:
    return OrderDetail.model_validate(
        await use_cases.add_dish(order_id, dish_id, quantity)
    )


@router.post("/{order_id}/drinks/{drink_id}", response_model=OrderDetail)
async def add_drink(
    order_id: UUID,
    drink_id: UUID,
    quantity: Annotated[int, Query(gt=0)],
    use_cases: FromDishka[OrderUseCases],
) -> OrderDetail:
    return OrderDetail.model_validate(
        await use_cases.add_drink(order_id, drink_id, quantity)
    )


@router.patch("/{order_id}/items/{item_id}", response_model=OrderDetail)
async def change_quantity(
    order_id: UUID,
    item_id: UUID,
    data: OrderItemQuantityUpdate,
    use_cases: FromDishka[OrderUseCases],
) -> OrderDetail:
    return OrderDetail.model_validate(
        await use_cases.change_item_quantity(order_id, item_id, data)
    )


@router.delete("/{order_id}/items/{item_id}", response_model=OrderDetail)
async def remove_item(
    order_id: UUID,
    item_id: UUID,
    use_cases: FromDishka[OrderUseCases],
) -> OrderDetail:
    return OrderDetail.model_validate(await use_cases.remove_item(order_id, item_id))


@router.post("/{order_id}/confirm", response_model=OrderDetail)
async def confirm_order(
    order_id: UUID,
    use_cases: FromDishka[OrderUseCases],
) -> OrderDetail:
    return OrderDetail.model_validate(await use_cases.confirm(order_id))
