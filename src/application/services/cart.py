from uuid import UUID

from src.application import messages
from src.domain.errors.does_not_exists import CustomDoesNotExist
from src.domain.errors.general import GeneralCustomError
from src.domain.models.choises.enum import OrderStatus
from src.domain.models.order import Order, OrderItem
from src.domain.ports.db.repositories.dish_repository import DishRepository
from src.domain.ports.db.repositories.drink_repository import DrinkRepository
from src.domain.ports.db.repositories.order_item_repository import (
    OrderItemRepository,
)
from src.domain.ports.db.repositories.order_repository import OrderRepository


class CartService:
    def __init__(
        self,
        order_repository: OrderRepository,
        order_item_repository: OrderItemRepository,
        dish_repository: DishRepository,
        drink_repository: DrinkRepository,
    ) -> None:
        self._orders = order_repository
        self._items = order_item_repository
        self._dishes = dish_repository
        self._drinks = drink_repository

    async def add_dish(
        self, order_id: UUID, dish_id: UUID, quantity: int
    ) -> Order:
        order = await self._get_editable_order(order_id)
        dish = await self._dishes.get_by_id(dish_id)
        if dish is None:
            raise CustomDoesNotExist(class_name="Dish", model_id=dish_id)
        if not dish.is_available:
            raise GeneralCustomError(
                text=messages.DISH_UNAVAILABLE, model_id=dish_id
            )

        item = next(
            (item for item in order.items if item.dish_id == dish_id), None
        )
        if item is None:
            item = OrderItem(
                dish_id=dish.id,
                title=dish.name,
                quantity=quantity,
                unit_price_minor=dish.price_minor,
            )
            order.items.append(item)
            await self._items.add(item)
        else:
            item.quantity += quantity
            await self._items.update(item)
        return await self._update_total(order)

    async def add_drink(
        self, order_id: UUID, drink_id: UUID, quantity: int
    ) -> Order:
        order = await self._get_editable_order(order_id)
        drink = await self._drinks.get_by_id(drink_id)
        if drink is None:
            raise CustomDoesNotExist(class_name="Drink", model_id=drink_id)
        if not drink.is_available:
            raise GeneralCustomError(
                text=messages.DRINK_UNAVAILABLE, model_id=drink_id
            )

        item = next(
            (item for item in order.items if item.drink_id == drink_id), None
        )
        if item is None:
            item = OrderItem(
                drink_id=drink.id,
                title=drink.name,
                quantity=quantity,
                unit_price_minor=drink.price_minor,
            )
            order.items.append(item)
            await self._items.add(item)
        else:
            item.quantity += quantity
            await self._items.update(item)
        return await self._update_total(order)

    async def change_quantity(
        self, order_id: UUID, item_id: UUID, quantity: int
    ) -> Order:
        order = await self._get_editable_order(order_id)
        item = self._get_item(order, item_id)
        item.quantity = quantity
        await self._items.update(item)
        return await self._update_total(order)

    async def remove_item(self, order_id: UUID, item_id: UUID) -> Order:
        order = await self._get_editable_order(order_id)
        item = self._get_item(order, item_id)
        order.items.remove(item)
        await self._items.delete(item)
        return await self._update_total(order)

    async def _get_editable_order(self, order_id: UUID) -> Order:
        order = await self._orders.get_by_id_for_update(order_id)
        if order is None:
            raise CustomDoesNotExist(class_name="Order", model_id=order_id)
        if order.status is not OrderStatus.pending:
            raise GeneralCustomError(
                text=messages.ORDER_NOT_EDITABLE, model_id=order_id
            )
        return order

    @staticmethod
    def _get_item(order: Order, item_id: UUID) -> OrderItem:
        item = next((item for item in order.items if item.id == item_id), None)
        if item is None:
            raise CustomDoesNotExist(class_name="OrderItem", model_id=item_id)
        return item

    async def _update_total(self, order: Order) -> Order:
        order.total_price_minor = sum(
            item.quantity * item.unit_price_minor for item in order.items
        )
        return await self._orders.update(order)
