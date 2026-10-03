"""Conversation orchestration: model decisions, checked actions, persistence."""

from __future__ import annotations

import re

from src.application.agent.actions import ActionExecutor
from src.application.agent.catalog import CatalogEntry, CatalogMatcher
from src.application.agent.constants import BRANCHES, MAX_HISTORY_TURNS
from src.application.agent.llm import ModelUnavailable, QwenAgentModel
from src.application.agent.messages import money_message
from src.application.agent.state import ConversationState, session_store
from src.application.logging import agent_log
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
        self._actions = ActionExecutor(self._catalog)
        self._orders = orders
        self._model = QwenAgentModel()

    @staticmethod
    def _menu_context(entries: list[CatalogEntry]) -> list[dict]:
        return [
            {
                **entry.as_context(),
                "price_spoken": money_message(entry.item.price_minor),
            }
            for entry in entries
        ]

    @staticmethod
    def _state_context(state: ConversationState) -> dict:
        missing = []
        if not state.lines:
            missing.append("items")
        if state.branch is None:
            missing.append("branch")
        if state.delivery_type is None:
            missing.append("delivery_type")
        if (
            state.delivery_type is DeliveryType.delivery
            and state.address is None
        ):
            missing.append("address_with_house_number")
        return {
            "cart": [
                {
                    "name": line.name,
                    "quantity": line.quantity,
                    "unit_price_minor": line.unit_price_minor,
                }
                for line in state.lines
            ],
            "subtotal": money_message(state.subtotal_minor),
            "branch": state.branch,
            "delivery_type": (
                state.delivery_type.value if state.delivery_type else None
            ),
            "address": state.address,
            "partial_address": state.address_street,
            "suggested_delivery": (
                state.suggested_delivery.value
                if state.suggested_delivery
                else None
            ),
            "missing_for_order": missing,
        }

    async def _create_order(
        self, session_id: str, state: ConversationState
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

    @staticmethod
    def _can_create(state: ConversationState) -> bool:
        return bool(
            state.lines
            and state.branch
            and state.delivery_type
            and (state.delivery_type is DeliveryType.pickup or state.address)
        )

    @staticmethod
    def _advice_about_fulfillment(context: dict) -> bool:
        question = context["customer_text"].lower()
        prior = (context.get("last_agent_question") or "").lower()
        asks_advice = any(
            phrase in question
            for phrase in (
                "что лучше",
                "посовету",
                "порекоменду",
                "что думаешь",
                "не знаю",
            )
        )
        offered_modes = "самовывоз" in prior and any(
            phrase in prior for phrase in ("достав", "на дом", "привез")
        )
        return asks_advice and offered_modes

    @staticmethod
    def _finished_adding(context: dict) -> bool:
        text = context["customer_text"].lower()
        prior = (context.get("last_agent_question") or "").lower()
        explicit = any(
            phrase in text
            for phrase in (
                "больше ничего",
                "ничего больше",
                "это всё",
                "это все",
                "достаточно",
            )
        )
        declined_more = text.strip() in ("нет", "не надо", "всё", "все")
        asked_more = any(
            phrase in prior
            for phrase in (
                "что-нибудь ещё",
                "что-нибудь еще",
                "что-то ещё",
                "что-то еще",
                "добавить",
            )
        )
        return explicit or (declined_more and asked_more)

    @staticmethod
    def _valid_reply(
        reply: str,
        order: Order | None,
        events: list[dict],
        history: list[tuple[str, str]],
        context: dict,
    ) -> bool:
        lowered = reply.lower()
        if not reply or len(reply) > 420 or "<think>" in lowered:
            return False
        if history and reply.strip() == history[-1][1].strip():
            return False
        if history and reply.lower().startswith(
            ("здравствуйте", "привет", "добрый день")
        ):
            return False
        if "100.00" in reply or "₽" in reply:
            return False
        if any(word in lowered for word in ("дешев", "быстр", "ветк")):
            return False
        if OrderAgent._advice_about_fulfillment(context) and not any(
            word in lowered
            for word in (
                "я бы",
                "совет",
                "рекоменд",
                "предлож",
                "если",
                "когда",
            )
        ):
            return False
        created_claim = any(
            phrase in lowered
            for phrase in (
                "заказ создан",
                "заказ принят",
                "заказ оформлен",
                "заказ подтвержд",
            )
        )
        if order is None and created_claim:
            return False
        if order is None and re.search(
            r"готовы оформить|подтверд\w* заказ", lowered
        ):
            return False
        if order is not None:
            return (
                "заказ" in lowered
                and money_message(order.total_price_minor) in lowered
            )
        added = any(
            event.get("action") == "add_item"
            and event.get("status") == "applied"
            for event in events
        )
        if not added and any(
            word in lowered for word in (
                "добавлен", "добавила", "записала", "добавляю",
                "добавляем", "записываю", "записано", "записан",
            )
        ):
            return False
        if added and any(
            phrase in lowered
            for phrase in (
                "хотите заказать его",
                "хотите заказать её",
                "добавить его",
                "добавить её",
                "добавить эту",
            )
        ):
            return False
        if added and not any(
            phrase in lowered
            for phrase in (
                "добавила",
                "добавлен",
                "добавлено",
                "записала",
                "в корзине",
                "в заказе",
                "готово",
            )
        ):
            return False
        state = context["state"]
        if "cart" in state and not state["cart"]:
            if re.search(
                r"(какую точку|выберите.*точк|назовите.*точк|"
                r"готовы оформить|подтверд\w* заказ|"
                r"доставка или самовывоз|на дом или.*самовывоз|"
                r"хотите что-нибудь ещё)",
                lowered,
            ):
                return False
        if context.get("ambiguous_items") and not added:
            if not any(
                name.lower() in lowered
                for name in context["ambiguous_items"]
            ):
                return False
        if (
            OrderAgent._finished_adding(context)
            and state.get("cart", True)
            and state["branch"] is None
            and (
                "точк" not in lowered
                and not any(
                    branch.lower() in lowered
                    for branch in context["branches"]
                )
            )
        ):
            return False
        if (
            OrderAgent._finished_adding(context)
            and state.get("cart", True)
            and any(
                phrase in lowered
                for phrase in (
                    "добавлен",
                    "добавила",
                    "добавлено",
                    "что-нибудь ещё",
                    "что-нибудь еще",
                    "что-то ещё",
                    "что-то еще",
                )
            )
        ):
            return False
        if (
            state["delivery_type"] == "delivery"
            and state["partial_address"]
            and not state["address"]
            and "дом" not in lowered
            and "номер" not in lowered
        ):
            return False
        if state["delivery_type"] == "pickup" and any(
            phrase in lowered
            for phrase in (
                "ваш адрес",
                "домашний адрес",
                "адрес доставки",
                "номер дома",
                "куда достав",
            )
        ):
            return False
        if (
            state["delivery_type"] == "delivery"
            and state["partial_address"]
            and not state["address"]
            and any(character.isdigit() for character in reply)
        ):
            return False
        branch = state["branch"]
        if branch:
            asks_branch_again = any(
                phrase in lowered
                for phrase in (
                    "какую точку",
                    "выбери точку",
                    "выберите точку",
                    "в какой точке",
                    "укажите точку",
                )
            )
            if asks_branch_again:
                return False
            wrong_branches = [
                candidate for candidate in BRANCHES if candidate != branch
            ]
            if any(
                f"вы выбрали точку «{candidate.lower()}»" in lowered
                or f'вы выбрали точку "{candidate.lower()}"' in lowered
                for candidate in wrong_branches
            ):
                return False
        return True

    async def _respond(
        self,
        context: dict,
        order: Order | None,
        events: list[dict],
        history: list[tuple[str, str]],
    ) -> str:
        for attempt in range(3):
            try:
                reply = await self._model.respond(context)
            except ModelUnavailable:
                break
            if self._valid_reply(reply, order, events, history, context):
                return reply
            guidance = ["Предыдущий ответ противоречил фактам или повторялся."]
            state = context["state"]
            if not state["cart"]:
                guidance.append(
                    "Корзина пуста. Сначала помоги выбрать товар. "
                    "Не переходи к точке, получению или подтверждению "
                    "и не утверждай, что что-либо добавлено."
                )
            if context.get("ambiguous_items"):
                guidance.append(
                    "Товар неоднозначен. Назови варианты из "
                    "ambiguous_items и попроси выбрать вид."
                )
            if state["partial_address"] and not state["address"]:
                guidance.append(
                    "Клиент назвал улицу, но не назвал номер дома. "
                    "Спроси номер, не выдумывай его."
                )
            if state["delivery_type"] == "pickup":
                guidance.append(
                    "Выбран самовывоз. Домашний адрес и номер дома "
                    "не нужны. Если точка ещё не выбрана, спроси только "
                    "точку ресторана из доступного списка."
                )
            if any(
                event.get("action") == "add_item"
                and event.get("status") == "applied"
                for event in events
            ):
                guidance.append(
                    "Товар уже добавлен. Подтверди это и естественно "
                    "спроси, хочет ли клиент добавить что-нибудь ещё. "
                    "Пока не спрашивай точку или способ получения."
                )
            if any(
                event.get("action") == "set_branch"
                and event.get("status") == "applied"
                and state["cart"]
                for event in events
            ):
                guidance.append("Точка уже выбрана. Спроси способ получения.")
            if (
                state["branch"]
                and state["cart"]
                and state["delivery_type"] is None
            ):
                guidance.append(
                    "Точка уже выбрана. Не спрашивай её повторно; "
                    "уточни только доставку или самовывоз."
                )
            if any(word in reply.lower() for word in ("быстр", "дешев")):
                guidance.append(
                    "Нет данных о скорости или выгоде. "
                    "Сравни только: самовывоз требует прийти на точку, "
                    "доставку привезут по адресу. Дай своё мнение."
                )
            if self._advice_about_fulfillment(context):
                guidance.append(
                    "Клиент просит твой личный совет о способе "
                    "получения. Назови один вариант и условие, "
                    "когда он удобен. Не повторяй просто выбор."
                )
            if self._finished_adding(context) and state["cart"]:
                guidance.append(
                    "Клиент закончил выбирать позиции, но не отменил "
                    "корзину. Не повторяй добавление и не спрашивай, "
                    "нужно ли что-то ещё. Уточни только недостающие "
                    "данные из missing_for_order. Если точка уже "
                    "выбрана, не спрашивай её повторно."
                )
            guidance.append("Не описывай отклонённое действие как выполненное.")
            context["correction"] = " ".join(guidance)
            context["rejected_reply"] = reply
        if order is not None:
            return (
                "Заказ создан. Итого "
                f"{money_message(order.total_price_minor)}."
            )
        return (
            "Извините, сейчас не получилось корректно ответить. "
            "Повторите, пожалуйста."
        )

    async def handle(self, session_id: str, text: str) -> AgentMessageResponse:
        state = session_store.get(session_id)
        agent_log.input(
            session_id,
            text,
            len(state.lines),
            state.branch,
            state.delivery_type,
            bool(state.address),
        )
        entries = await self._catalog.entries()
        history = state.history[-MAX_HISTORY_TURNS:]
        menu = self._menu_context(entries)
        if state.pending_item_text and re.fullmatch(
            r"(классич\w*|обычн\w*|остр\w*)[.!? ]*", text.lower()
        ):
            # Resolve a requested variant, retaining the original quantity.
            text = f"{state.pending_item_text} {text}"
        recognized = await self._catalog.find(text)
        ambiguous_items = (
            await self._catalog.suggestions(text) if recognized is None else []
        )
        if len(ambiguous_items) < 2:
            ambiguous_items = []
        else:
            state.pending_item_text = text
        recognized_item = next(
            (
                {"sku": entry.sku, "name": entry.item.name}
                for entry in entries
                if recognized and entry.item.id == recognized.item.id
            ),
            None,
        )
        planner_context = {
            "customer_text": text,
            "history": history,
            "state": self._state_context(state),
            "menu": menu,
            "branches": BRANCHES,
            "recognized_item": recognized_item,
            "ambiguous_items": ambiguous_items,
        }
        try:
            plan = await self._model.plan(planner_context)
        except ModelUnavailable:
            reply = (
                "Извините, сейчас не могу обработать заказ. "
                "Попробуйте ещё раз через минуту."
            )
            agent_log.reply(session_id, "model_unavailable", reply)
            return AgentMessageResponse(
                session_id=session_id,
                reply=reply,
                cart=state.labels,
            )
        agent_log.extraction(session_id, plan)
        events = await self._actions.apply(plan, text, state, entries)
        if events and all(
            event.get("status") == "rejected" for event in events
        ):
            planner_context["validation_feedback"] = events
            try:
                revised = await self._model.plan(planner_context)
            except ModelUnavailable:
                revised = None
            if revised is not None:
                agent_log.extraction(session_id, revised)
                plan = revised
                events = await self._actions.apply(
                    revised, text, state, entries
                )
        agent_log.actions(session_id, events)
        if any(
            event.get("action") == "add_item"
            and event.get("status") == "applied"
            for event in events
        ):
            state.pending_item_text = None
        order = None
        if self._can_create(state):
            order = await self._create_order(session_id, state)
        labels = state.labels
        response_context = {
            "customer_text": text,
            "history": history,
            "last_agent_question": history[-1][1] if history else None,
            "intent": plan.get("intent"),
            "verified_events": events,
            "state": self._state_context(state),
            "available_menu": [
                {
                    "name": entry.item.name,
                    "price": money_message(entry.item.price_minor),
                }
                for entry in entries
                if entry.item.is_available
            ],
            "branches": BRANCHES,
            "recognized_item": recognized_item,
            "ambiguous_items": ambiguous_items,
            "order_created": order is not None,
            "order_id": str(order.id) if order else None,
            "exact_total": (
                money_message(order.total_price_minor) if order else None
            ),
        }
        reply = await self._respond(response_context, order, events, history)
        agent_log.reply(session_id, "model", reply)
        if order is None:
            state.history.append((text, reply))
            state.history = state.history[-MAX_HISTORY_TURNS:]
        else:
            session_store.remove(session_id)
        return AgentMessageResponse(
            session_id=session_id,
            reply=reply,
            order_id=order.id if order else None,
            cart=labels,
        )
