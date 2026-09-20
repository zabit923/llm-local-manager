import asyncio
from uuid import UUID, uuid4

from sqlalchemy.orm import configure_mappers

from src.application.services.cart import CartService
from src.domain.models.choises.enum import OrderStatus
from src.domain.models.dish import Dish
from src.domain.models.drinks import Drink
from src.domain.models.order import Order, OrderItem


class FakeOrderRepository:
    def __init__(self, order: Order) -> None:
        self.order = order

    async def get_by_id_for_update(self, order_id: UUID) -> Order | None:
        return self.order if order_id == self.order.id else None

    async def update(self, order: Order) -> Order:
        return order


class FakeOrderItemRepository:
    async def add(self, item: OrderItem) -> OrderItem:
        item.id = item.id or uuid4()
        return item

    async def update(self, item: OrderItem) -> OrderItem:
        return item

    async def delete(self, item: OrderItem) -> None:
        return None


class FakeDishRepository:
    def __init__(self, dish: Dish) -> None:
        self.dish = dish

    async def get_by_id(self, dish_id: UUID) -> Dish | None:
        return self.dish if dish_id == self.dish.id else None


class FakeDrinkRepository:
    def __init__(self, drink: Drink) -> None:
        self.drink = drink

    async def get_by_id(self, drink_id: UUID) -> Drink | None:
        return self.drink if drink_id == self.drink.id else None


def test_cart_merges_duplicate_items_and_recalculates_total() -> None:
    async def scenario() -> None:
        configure_mappers()
        order = Order(
            id=uuid4(),
            status=OrderStatus.pending,
            branch="Ермошкина",
        )
        dish = Dish(
            id=uuid4(),
            name="Острый гиро",
            price_minor=35000,
            is_available=True,
        )
        drink = Drink(
            id=uuid4(),
            name="Кола",
            volume_ml=500,
            price_minor=15000,
            is_available=True,
        )
        cart = CartService(
            FakeOrderRepository(order),
            FakeOrderItemRepository(),
            FakeDishRepository(dish),
            FakeDrinkRepository(drink),
        )

        await cart.add_dish(order.id, dish.id, quantity=2)
        await cart.add_dish(order.id, dish.id, quantity=1)
        await cart.add_drink(order.id, drink.id, quantity=2)

        assert len(order.items) == 2
        assert order.items[0].quantity == 3
        assert order.total_price_minor == 135000

    asyncio.run(scenario())
