from src.application.agent.conversation.state import ConversationState
from src.application.logging import agent_log
from src.application.schemas.orders import OrderCreate
from src.application.use_cases.orders import OrderUseCases
from src.domain.models.choises.enum import DeliveryType
from src.domain.models.order import Order


class CheckoutService:

    def __init__(self, orders: OrderUseCases) -> None:
        self._orders = orders

    @staticmethod
    def ready(state: ConversationState) -> bool:
        return bool(
            state.lines
            and state.branch
            and state.delivery_type
            and (state.delivery_type is DeliveryType.pickup or state.address)
        )

    async def create_if_ready(
        self,
        session_id: str,
        state: ConversationState,
    ) -> Order | None:
        if not self.ready(state):
            return None
        order = await self._orders.create_confirmed(
            OrderCreate(
                branch=state.branch,
                delivery_type=state.delivery_type,
                address=state.address,
                items=state.items,
            )
        )
        agent_log.completed(session_id, order.id)
        return order
