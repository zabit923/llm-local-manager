from __future__ import annotations

from src.application.agent.catalog import CatalogMatcher, QuantityParser
from src.application.agent.constants import (
    ADDRESS_KEYWORD,
    BRANCHES,
    CONFIRMATION_KEYWORDS,
    DELIVERY_KEYWORD,
    DELIVERY_LABEL,
    PICKUP_KEYWORDS,
    PICKUP_LABEL,
    UNAVAILABLE_KIND,
)
from src.application.agent.llm import QwenOrderExtractor
from src.application.logging import agent_log
from src.application.agent.messages import (
    ADDRESS_PROMPT,
    DELIVERY_PROMPT,
    ORDER_START_PROMPT,
    branch_prompt,
    confirm_message,
    item_label,
    item_added_message,
    order_accepted_message,
    unavailable_message,
)
from src.application.agent.state import session_store
from src.application.schemas.agent import AgentMessageResponse
from src.application.schemas.orders import OrderCreate
from src.application.use_cases.dishes import DishUseCases
from src.application.use_cases.drinks import DrinkUseCases
from src.application.use_cases.orders import OrderUseCases
from src.domain.models.choises.enum import DeliveryType


class OrderAgent:
    def __init__(
        self, dishes: DishUseCases, drinks: DrinkUseCases, orders: OrderUseCases
    ) -> None:
        self._catalog = CatalogMatcher(dishes, drinks)
        self._orders = orders
        self._extractor = QwenOrderExtractor()

    async def handle(self, session_id: str, text: str) -> AgentMessageResponse:
        state = session_store.get(session_id)
        lowered = text.lower().strip()
        agent_log.input(
            session_id,
            text,
            len(state.items),
            state.branch,
            state.delivery_type,
            bool(state.address),
        )

        if state.items:
            if state.branch is None:
                state.branch = next(
                    (
                        branch
                        for branch in BRANCHES
                        if branch.lower() in lowered
                    ),
                    None,
                )
                agent_log.branch_parsed(session_id, state.branch)
                if state.branch is None:
                    return AgentMessageResponse(
                        session_id=session_id,
                        reply=branch_prompt(),
                        cart=state.labels,
                    )

            if state.delivery_type is None:
                if any(word in lowered for word in PICKUP_KEYWORDS):
                    state.delivery_type = DeliveryType.pickup
                elif DELIVERY_KEYWORD in lowered:
                    state.delivery_type = DeliveryType.delivery
                else:
                    return AgentMessageResponse(
                        session_id=session_id,
                        reply=DELIVERY_PROMPT,
                        cart=state.labels,
                    )
                agent_log.delivery_parsed(session_id, state.delivery_type)

            if (
                state.delivery_type == DeliveryType.delivery
                and state.address is None
            ):
                if ADDRESS_KEYWORD not in lowered and len(text.split()) < 2:
                    return AgentMessageResponse(
                        session_id=session_id,
                        reply=ADDRESS_PROMPT,
                        cart=state.labels,
                    )
                state.address = text.strip()
                agent_log.address_saved(session_id)

        if state.items and state.branch and state.delivery_type:
            if any(word in lowered for word in CONFIRMATION_KEYWORDS):
                agent_log.confirms(session_id)
                order = await self._orders.create(
                    OrderCreate(
                        branch=state.branch,
                        delivery_type=state.delivery_type,
                        address=state.address,
                        items=state.items,
                    )
                )
                order = await self._orders.confirm(order.id)
                session_store.remove(session_id)
                agent_log.completed(session_id, order.id)
                return AgentMessageResponse(
                    session_id=session_id,
                    reply=order_accepted_message(order.id),
                    order_id=order.id,
                )
            delivery_label = (
                DELIVERY_LABEL
                if state.delivery_type == DeliveryType.delivery
                else PICKUP_LABEL
            )
            return AgentMessageResponse(
                session_id=session_id,
                reply=confirm_message(
                    state.labels, state.branch, delivery_label
                ),
                cart=state.labels,
            )

        extracted = await self._extractor.extract(text)
        agent_log.extraction(session_id, extracted)
        item_text = extracted.name if extracted else text
        quantity = (
            extracted.quantity if extracted else QuantityParser.parse(text)
        )
        match = await self._catalog.find(item_text)
        agent_log.catalog_match(session_id, item_text, match)
        if match is None:
            return AgentMessageResponse(
                session_id=session_id,
                reply=ORDER_START_PROMPT,
                cart=state.labels,
            )
        if match.kind == UNAVAILABLE_KIND:
            return AgentMessageResponse(
                session_id=session_id,
                reply=unavailable_message(match.item.name),
                cart=state.labels,
            )

        state.items.append(self._catalog.to_order_item(match, quantity))
        state.labels.append(item_label(match.item.name, quantity))
        agent_log.item_added(session_id, match.item.name, quantity)
        return AgentMessageResponse(
            session_id=session_id,
            reply=item_added_message(match.item.name, quantity),
            cart=state.labels,
        )
