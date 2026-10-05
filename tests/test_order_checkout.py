from uuid import uuid4

import pytest
from sqlalchemy.orm import configure_mappers

from src.application.schemas.orders import OrderCreate, OrderItemCreate
from src.application.services.cart import CartService
from src.application.use_cases.orders import OrderUseCases
from src.domain.errors.general import GeneralCustomError
from src.domain.models.choises.enum import DeliveryType, OrderStatus
from src.domain.models.dish import Dish


class OrderRepository:
    def __init__(self):
        self.order = None

    async def add(self, order):
        order.id = uuid4()
        self.order = order
        return order

    async def get_by_id(self, _order_id):
        return self.order

    async def get_by_id_for_update(self, _order_id):
        return self.order

    async def update(self, order):
        return order


class ItemRepository:
    async def add(self, item):
        item.id = uuid4()
        return item


class MenuRepository:
    def __init__(self, item):
        self.item = item

    async def get_by_id(self, _item_id):
        return self.item


class Committer:
    def __init__(self, repository):
        self.repository = repository
        self.commits = []

    async def commit(self):
        self.commits.append(self.repository.order.status)


def checkout(available=True):
    configure_mappers()
    dish = Dish(
        id=uuid4(),
        name="Гирос",
        price_minor=35000,
        is_available=available,
    )
    repository = OrderRepository()
    committer = Committer(repository)
    cart = CartService(
        repository,
        ItemRepository(),
        MenuRepository(dish),
        MenuRepository(None),
    )
    orders = OrderUseCases(repository, cart, committer)
    return dish, orders, committer


@pytest.mark.asyncio
async def test_confirmed_order_and_items_are_committed_together():
    dish, orders, committer = checkout()
    order = await orders.create_confirmed(
        OrderCreate(
            branch="Ермошкина",
            delivery_type=DeliveryType.pickup,
            items=[OrderItemCreate(dish_id=dish.id, quantity=2)],
        )
    )
    assert committer.commits == [OrderStatus.confirmed]
    assert order.total_price_minor == 70000
    assert order.items[0].quantity == 2


@pytest.mark.asyncio
async def test_failed_checkout_does_not_commit_a_draft():
    dish, orders, committer = checkout(available=False)
    with pytest.raises(GeneralCustomError):
        await orders.create_confirmed(
            OrderCreate(
                branch="Ермошкина",
                delivery_type=DeliveryType.pickup,
                items=[OrderItemCreate(dish_id=dish.id, quantity=1)],
            )
        )
    assert committer.commits == []
