from __future__ import annotations

from src.application.agent.catalog import CatalogMatcher, QuantityParser
from src.application.agent.constants import (
    ADDRESS_KEYWORD,
    BRANCHES,
    DELIVERY_KEYWORD,
    DELIVERY_LABEL,
    MENU_KEYWORDS,
    NO_ORDER_KEYWORDS,
    PICKUP_KEYWORDS,
    STAGE_ASK_ADDRESS,
    STAGE_ASK_BRANCH,
    STAGE_ASK_DELIVERY,
    STAGE_ASK_ORDER,
    STAGE_ITEM_ADDED,
    STAGE_ORDER_ACCEPTED,
    STAGE_UNAVAILABLE,
    UNAVAILABLE_KIND,
)
from src.application.agent.llm import QwenOrderExtractor
from src.application.logging import agent_log
from src.application.agent.messages import (
    ADDRESS_PROMPT,
    DELIVERY_PROMPT,
    NO_ORDER_PROMPT,
    branch_prompt,
    item_label,
    item_added_message,
    menu_message,
    not_found_message,
    order_created_message,
    unavailable_message,
)
from src.application.agent.state import ConversationState, session_store
from src.application.schemas.agent import AgentMessageResponse
from src.application.schemas.orders import OrderCreate
from src.application.use_cases.dishes import DishUseCases
from src.application.use_cases.drinks import DrinkUseCases
from src.application.use_cases.orders import OrderUseCases
from src.domain.models.choises.enum import DeliveryType
from src.domain.models.order import Order


class OrderAgent:
    def __init__(
        self, dishes: DishUseCases, drinks: DrinkUseCases, orders: OrderUseCases
    ) -> None:
        self._catalog = CatalogMatcher(dishes, drinks)
        self._orders = orders
        self._extractor = QwenOrderExtractor()

    async def _response(
        self,
        session_id: str,
        text: str,
        stage: str,
        fallback: str,
        cart: list[str],
        facts: dict[str, str] | None = None,
        order_id: object | None = None,
    ) -> AgentMessageResponse:
        reply = await self._extractor.reply(
            customer_text=text,
            stage=stage,
            cart=cart,
            facts=facts or {},
            fallback=fallback,
        )
        agent_log.reply(session_id, stage, reply)
        return AgentMessageResponse(
            session_id=session_id,
            reply=reply,
            order_id=order_id,
            cart=cart,
        )

    async def _create_order(
        self,
        session_id: str,
        state: ConversationState,
    ) -> Order:
        order = await self._orders.create(
            OrderCreate(
                branch=state.branch,
                delivery_type=state.delivery_type,
                address=state.address,
                items=state.items,
            )
        )
        order = await self._orders.confirm(order.id)
        agent_log.completed(session_id, order.id)
        return order

    def _created_response(
        self,
        session_id: str,
        order: Order,
        labels: list[str],
    ) -> AgentMessageResponse:
        reply = order_created_message(order.total_price_minor)
        agent_log.reply(session_id, STAGE_ORDER_ACCEPTED, reply)
        return AgentMessageResponse(
            session_id=session_id,
            reply=reply,
            order_id=order.id,
            cart=labels,
        )

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
                    return await self._response(
                        session_id,
                        text,
                        STAGE_ASK_BRANCH,
                        branch_prompt(),
                        state.labels,
                        {"available_branches": ", ".join(BRANCHES)},
                    )

            if state.delivery_type is None:
                if any(word in lowered for word in PICKUP_KEYWORDS):
                    state.delivery_type = DeliveryType.pickup
                elif DELIVERY_KEYWORD in lowered:
                    state.delivery_type = DeliveryType.delivery
                else:
                    return await self._response(
                        session_id,
                        text,
                        STAGE_ASK_DELIVERY,
                        DELIVERY_PROMPT,
                        state.labels,
                        {"branch": state.branch},
                    )
                agent_log.delivery_parsed(session_id, state.delivery_type)
                if state.delivery_type == DeliveryType.pickup:
                    order = await self._create_order(session_id, state)
                    labels = state.labels.copy()
                    session_store.remove(session_id)
                    return self._created_response(session_id, order, labels)

            if (
                state.delivery_type == DeliveryType.delivery
                and state.address is None
            ):
                if ADDRESS_KEYWORD not in lowered and len(text.split()) < 2:
                    return await self._response(
                        session_id,
                        text,
                        STAGE_ASK_ADDRESS,
                        ADDRESS_PROMPT,
                        state.labels,
                        {
                            "branch": state.branch,
                            "delivery_type": DELIVERY_LABEL,
                        },
                    )
                state.address = text.strip()
                agent_log.address_saved(session_id)
                order = await self._create_order(session_id, state)
                labels = state.labels.copy()
                session_store.remove(session_id)
                return self._created_response(session_id, order, labels)

        if any(keyword in lowered for keyword in MENU_KEYWORDS):
            names = await self._catalog.available_names()
            return await self._response(
                session_id,
                text,
                STAGE_ASK_ORDER,
                menu_message(names),
                state.labels,
                {"available_menu": ", ".join(names)},
            )

        if any(keyword in lowered for keyword in NO_ORDER_KEYWORDS):
            return await self._response(
                session_id,
                text,
                STAGE_ASK_ORDER,
                NO_ORDER_PROMPT,
                state.labels,
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
            names = await self._catalog.available_names()
            return await self._response(
                session_id,
                text,
                STAGE_UNAVAILABLE,
                not_found_message(item_text, names),
                state.labels,
                {
                    "requested_item": item_text,
                    "available_menu": ", ".join(names),
                },
            )
        if match.kind == UNAVAILABLE_KIND:
            return await self._response(
                session_id,
                text,
                STAGE_UNAVAILABLE,
                unavailable_message(match.item.name),
                state.labels,
                {"item": match.item.name, "available": "нет"},
            )

        state.items.append(self._catalog.to_order_item(match, quantity))
        state.labels.append(item_label(match.item.name, quantity))
        agent_log.item_added(session_id, match.item.name, quantity)
        return await self._response(
            session_id,
            text,
            STAGE_ITEM_ADDED,
            item_added_message(match.item.name, quantity),
            state.labels,
            {
                "item": match.item.name,
                "quantity": str(quantity),
            },
        )
