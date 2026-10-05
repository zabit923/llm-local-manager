from uuid import UUID

from src.application import messages
from src.application.schemas.orders import OrderCreate, OrderItemQuantityUpdate
from src.application.services.cart import CartService
from src.domain.errors.does_not_exists import CustomDoesNotExist
from src.domain.errors.general import GeneralCustomError
from src.domain.models.choises.enum import DeliveryType, OrderStatus
from src.domain.models.order import Order
from src.domain.ports.db.commiter import Commiter
from src.domain.ports.db.repositories.order_repository import OrderRepository


class OrderUseCases:
    def __init__(
        self,
        repository: OrderRepository,
        cart_service: CartService,
        commiter: Commiter,
    ) -> None:
        self._repository = repository
        self._cart = cart_service
        self._commiter = commiter

    async def create(self, data: OrderCreate) -> Order:
        order = await self._build_order(data)
        await self._commiter.commit()
        return await self.get(order.id)

    async def create_confirmed(self, data: OrderCreate) -> Order:
        order = await self._build_order(data)
        self._confirm_order(order)
        await self._repository.update(order)
        await self._commiter.commit()
        return await self.get(order.id)

    async def _build_order(self, data: OrderCreate) -> Order:
        order = Order(
            status=OrderStatus.pending,
            customer_name=data.customer_name,
            branch=data.branch,
            comment=data.comment,
            delivery_type=data.delivery_type,
            address=data.address,
            payment_method=data.payment_method,
            items=[],
        )
        await self._repository.add(order)
        for item in data.items:
            if item.dish_id is not None:
                await self._cart.add_dish(order.id, item.dish_id, item.quantity)
            elif item.drink_id is not None:
                await self._cart.add_drink(
                    order.id, item.drink_id, item.quantity
                )

        return order

    async def get(self, order_id: UUID) -> Order:
        order = await self._repository.get_by_id(order_id)
        if order is None:
            raise CustomDoesNotExist(class_name="Order", model_id=order_id)
        return order

    async def list_all(self) -> list[Order]:
        return await self._repository.list_all()

    async def add_dish(
        self, order_id: UUID, dish_id: UUID, quantity: int
    ) -> Order:
        order = await self._cart.add_dish(order_id, dish_id, quantity)
        await self._commiter.commit()
        return order

    async def add_drink(
        self, order_id: UUID, drink_id: UUID, quantity: int
    ) -> Order:
        order = await self._cart.add_drink(order_id, drink_id, quantity)
        await self._commiter.commit()
        return order

    async def change_item_quantity(
        self,
        order_id: UUID,
        item_id: UUID,
        data: OrderItemQuantityUpdate,
    ) -> Order:
        order = await self._cart.change_quantity(
            order_id, item_id, data.quantity
        )
        await self._commiter.commit()
        return order

    async def remove_item(self, order_id: UUID, item_id: UUID) -> Order:
        order = await self._cart.remove_item(order_id, item_id)
        await self._commiter.commit()
        return order

    async def confirm(self, order_id: UUID) -> Order:
        order = await self._repository.get_by_id_for_update(order_id)
        if order is None:
            raise CustomDoesNotExist(class_name="Order", model_id=order_id)
        self._confirm_order(order)
        await self._repository.update(order)
        await self._commiter.commit()
        return order

    @staticmethod
    def _confirm_order(order: Order) -> None:
        if order.status is not OrderStatus.pending:
            raise GeneralCustomError(
                text=messages.ORDER_NOT_PENDING, model_id=order.id
            )
        if not order.items:
            raise GeneralCustomError(
                text=messages.EMPTY_ORDER, model_id=order.id
            )
        if order.delivery_type is DeliveryType.delivery and not order.address:
            raise GeneralCustomError(
                text=messages.DELIVERY_ADDRESS_REQUIRED, model_id=order.id
            )

        order.status = OrderStatus.confirmed
