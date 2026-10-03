from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.application.agent.catalog import CatalogMatcher
from src.application.agent.llm import ModelUnavailable
from src.application.agent.messages import money_message
from src.application.agent.service import OrderAgent
from src.application.agent.state import session_store


class Menu:
    def __init__(self, names: list[str]) -> None:
        self.items = [
            SimpleNamespace(
                id=uuid4(),
                name=name,
                is_available=True,
                price_minor=10000,
            )
            for name in names
        ]

    async def list(self) -> list[SimpleNamespace]:
        return self.items


class Orders:
    def __init__(self) -> None:
        self.created = []

    async def create(self, data):
        self.created.append(data)
        return SimpleNamespace(id=uuid4(), total_price_minor=45000)

    async def confirm(self, order_id):
        return SimpleNamespace(id=order_id, total_price_minor=45000)


class Model:
    def __init__(self, plans: dict[str, dict]) -> None:
        self.plans = plans
        self.contexts: list[dict] = []

    async def plan(self, context: dict) -> dict:
        self.contexts.append(context)
        return self.plans.get(
            context["customer_text"],
            {"intent": "conversation", "actions": []},
        )

    async def respond(self, context: dict) -> str:
        if context["order_created"]:
            return f"Заказ создан. Итого {context['exact_total']}."
        text = context["customer_text"]
        if text == "что порекомендуешь":
            return "Я бы посоветовала самовывоз, если удобно зайти."
        for event in context["verified_events"]:
            if event["action"] == "add_item" and (
                event["status"] == "applied"
            ):
                return f"Добавила {event['item']} в корзину."
            if event["action"] == "set_branch" and (
                event["status"] == "applied"
            ):
                return "Точка выбрана. Доставка или самовывоз?"
            if event["action"] == "set_address" and (
                event["status"] == "incomplete"
            ):
                return "Уточните номер дома, пожалуйста."
        return "Я вас слушаю. Расскажите, что хочется заказать."


def item_action(sku: str, evidence: str, quantity: int = 1) -> dict:
    return {
        "name": "add_item",
        "sku": sku,
        "quantity": quantity,
        "evidence": evidence,
    }


def branch_action(branch: str, evidence: str) -> dict:
    return {
        "name": "set_branch",
        "branch": branch,
        "evidence": evidence,
    }


def delivery_action(value: str, evidence: str) -> dict:
    return {
        "name": "set_delivery",
        "value": value,
        "evidence": evidence,
    }


def make_agent(plans: dict[str, dict]) -> tuple[OrderAgent, Orders, Model]:
    orders = Orders()
    model = Model(plans)
    agent = OrderAgent(
        Menu(["Классический гирос", "Острый гирос"]),
        Menu(["Вода", "Кола"]),
        orders,
    )
    agent._model = model
    return agent, orders, model


def test_spoken_price() -> None:
    assert money_message(10000) == "100 рублей"
    assert money_message(10100) == "101 рубль"
    assert money_message(10250) == "102 рубля 50 копеек"


@pytest.mark.parametrize("reply", [
    "Хорошо, добавляю один гирос. Хотите что-нибудь ещё?",
    "Самовывоз выбран. Готовы оформить заказ?",
    "Выберите, где хотите получить заказ. Выберите точку.",
    "Выберите, хотите ли получить его на дом или в самовывоз.",
    "Заказ оформлен. Сумма 630 рублей.",
])
def test_empty_cart_rejects_false_progress_from_logs(reply):
    context = {
        "customer_text": "Один гиро.",
        "last_agent_question": None,
        "state": {
            "cart": [], "branch": None, "delivery_type": None,
            "partial_address": None, "address": None,
        },
    }
    assert not OrderAgent._valid_reply(reply, None, [], [], context)


@pytest.mark.asyncio
async def test_ambiguous_gyro_clarification_then_pickup_creates_order():
    plans = {
        "Один гиро.": {"actions": [item_action("D2", "Один гиро")]},
        "Один гиро. классический": {
            "actions": [item_action("D1", "Один гиро. классический")],
        },
        "Ермошкина.": {
            "actions": [branch_action("Ермошкина", "Ермошкина")],
        },
        "Самовоз.": {
            "actions": [delivery_action("pickup", "Самовоз")],
        },
    }
    agent, orders, model = make_agent(plans)
    original_reply = model.respond

    async def respond(context):
        if context.get("ambiguous_items"):
            return "Какой гирос: Классический гирос или Острый гирос?"
        return await original_reply(context)

    model.respond = respond
    session = str(uuid4())
    first = await agent.handle(session, "Один гиро.")
    assert first.cart == []
    assert "Какой гирос" in first.reply
    selected = await agent.handle(session, "классический")
    assert selected.cart == ["1 Классический гирос"]
    await agent.handle(session, "Ермошкина.")
    final = await agent.handle(session, "Самовоз.")
    assert final.order_id is not None
    assert len(orders.created) == 1
    assert orders.created[0].delivery_type.value == "pickup"
    assert orders.created[0].address is None


def test_pickup_reply_cannot_request_home_address() -> None:
    context = {
        "customer_text": "самовывоз",
        "state": {
            "delivery_type": "pickup",
            "partial_address": None,
            "address": None,
            "branch": None,
        },
    }
    valid = OrderAgent._valid_reply(
        "Назовите ваш адрес и номер дома.",
        None,
        [],
        [],
        context,
    )
    assert not valid


def test_finished_cart_reply_moves_to_branch_without_repeating_item() -> None:
    context = {
        "customer_text": "больше ничего",
        "last_agent_question": "Хотите добавить что-нибудь ещё?",
        "branches": ("Ермошкина", "Центральная"),
        "state": {
            "delivery_type": None,
            "partial_address": None,
            "address": None,
            "branch": None,
        },
    }
    repeated = OrderAgent._valid_reply(
        "Гирос добавлен. Хотите что-нибудь ещё?",
        None,
        [],
        [],
        context,
    )
    continued = OrderAgent._valid_reply(
        "Хорошо. Какую точку выберете: Ермошкина или Центральная?",
        None,
        [],
        [],
        context,
    )
    assert not repeated
    assert continued


@pytest.mark.asyncio
async def test_catalog_does_not_turn_air_into_water() -> None:
    catalog = CatalogMatcher(
        Menu(["Классический гирос", "Острый гирос"]),
        Menu(["Вода", "Кола"]),
    )
    assert await catalog.find("воздух") is None
    assert await catalog.find("ничего") is None
    assert await catalog.find("гиро") is None
    assert (await catalog.find("обычный герой")).item.name == (
        "Классический гирос"
    )


@pytest.mark.asyncio
async def test_model_drives_reply_and_no_action_for_advice() -> None:
    plans = {
        "что порекомендуешь": {
            "intent": "give_advice",
            "actions": [],
            "suggested_delivery": "pickup",
        },
    }
    agent, orders, model = make_agent(plans)
    session_id = str(uuid4())
    result = await agent.handle(session_id, "что порекомендуешь")
    assert "Я бы посоветовала" in result.reply
    assert not orders.created
    assert model.contexts[0]["menu"]
    session_store.remove(session_id)


@pytest.mark.asyncio
async def test_model_cannot_hallucinate_cart_item() -> None:
    plans = {
        "воздух": {
            "intent": "order",
            "actions": [item_action("R1", "воздух")],
        },
    }
    agent, orders, _ = make_agent(plans)
    session_id = str(uuid4())
    result = await agent.handle(session_id, "воздух")
    assert not result.cart
    assert not orders.created
    session_store.remove(session_id)


@pytest.mark.asyncio
async def test_multiple_items_and_pickup_create_order() -> None:
    phrase = "два острых гироса и одну колу"
    plans = {
        phrase: {
            "intent": "order",
            "actions": [
                item_action("D2", "два острых гироса", 2),
                item_action("R2", "одну колу"),
            ],
        },
        "Центрально": {
            "intent": "choose_branch",
            "actions": [branch_action("Центральная", "Центрально")],
        },
        "самовывоз": {
            "intent": "choose_pickup",
            "actions": [delivery_action("pickup", "самовывоз")],
        },
    }
    agent, orders, _ = make_agent(plans)
    session_id = str(uuid4())
    first = await agent.handle(session_id, phrase)
    assert first.cart == ["2 Острый гирос", "1 Кола"]
    assert "Добавила" in first.reply
    await agent.handle(session_id, "Центрально")
    final = await agent.handle(session_id, "самовывоз")
    assert final.order_id is not None
    assert "450 рублей" in final.reply
    assert len(orders.created) == 1
    session_store.remove(session_id)


@pytest.mark.asyncio
async def test_misrecognized_pickup_word_creates_pickup_order() -> None:
    plans = {
        "вода": {
            "intent": "order",
            "actions": [item_action("R1", "вода")],
        },
        "Ермошкина": {
            "intent": "branch",
            "actions": [branch_action("Ермошкина", "Ермошкина")],
        },
        "самого": {
            "intent": "pickup",
            "actions": [delivery_action("pickup", "самого")],
        },
    }
    agent, orders, _ = make_agent(plans)
    session_id = str(uuid4())
    await agent.handle(session_id, "вода")
    await agent.handle(session_id, "Ермошкина")
    result = await agent.handle(session_id, "самого")
    assert result.order_id is not None
    assert orders.created[0].delivery_type.value == "pickup"
    assert orders.created[0].address is None
    session_store.remove(session_id)


@pytest.mark.asyncio
async def test_branch_name_can_be_partial_delivery_address() -> None:
    plans = {
        "вода": {
            "intent": "order", "actions": [item_action("R1", "вода")]
        },
        "Центральная": {
            "intent": "branch", "actions": [
                branch_action("Центральная", "Центральная")
            ],
        },
        "доставка": {
            "intent": "delivery", "actions": [
                delivery_action("delivery", "доставка")
            ],
        },
        "Ермошкина": {
            "intent": "mistaken branch", "actions": [
                branch_action("Ермошкина", "Ермошкина")
            ],
        },
        "17А": {
            "intent": "address", "actions": [
                {"name": "set_address", "value": "17А"}
            ],
        },
    }
    agent, orders, _ = make_agent(plans)
    session_id = str(uuid4())
    for phrase in ("вода", "Центральная", "доставка"):
        await agent.handle(session_id, phrase)
    partial = await agent.handle(session_id, "Ермошкина")
    assert partial.order_id is None
    assert "номер дома" in partial.reply
    final = await agent.handle(session_id, "17А")
    assert final.order_id is not None
    assert orders.created[0].branch == "Центральная"
    assert orders.created[0].address == "Ермошкина, дом 17А"
    session_store.remove(session_id)


@pytest.mark.asyncio
async def test_address_requires_house_number() -> None:
    plans = {
        "вода": {"intent": "order", "actions": [item_action("R1", "вода")]},
        "Центральная": {
            "intent": "choose_branch",
            "actions": [branch_action("Центральная", "Центральная")],
        },
        "доставка": {
            "intent": "choose_delivery",
            "actions": [delivery_action("delivery", "доставка")],
        },
        "Ермошкина": {
            "intent": "address",
            "actions": [{"name": "set_address", "value": "Ермошкина"}],
        },
        "17А": {
            "intent": "address",
            "actions": [{"name": "set_address", "value": "17А"}],
        },
    }
    agent, orders, _ = make_agent(plans)
    session_id = str(uuid4())
    for phrase in ("вода", "Центральная", "доставка"):
        await agent.handle(session_id, phrase)
    partial = await agent.handle(session_id, "Ермошкина")
    assert partial.order_id is None
    final = await agent.handle(session_id, "17А")
    assert final.order_id is not None
    assert orders.created[0].address == "Ермошкина, дом 17А"
    session_store.remove(session_id)


@pytest.mark.asyncio
async def test_pickup_never_accepts_customer_address() -> None:
    plans = {
        "вода": {"intent": "order", "actions": [item_action("R1", "вода")]},
        "самовывоз": {
            "intent": "pickup",
            "actions": [delivery_action("pickup", "самовывоз")],
        },
        "Ленина 10": {
            "intent": "address",
            "actions": [
                {"name": "set_address", "value": "Ленина 10"},
            ],
        },
    }
    agent, orders, _ = make_agent(plans)
    session_id = str(uuid4())
    await agent.handle(session_id, "вода")
    await agent.handle(session_id, "самовывоз")
    result = await agent.handle(session_id, "Ленина 10")
    state = session_store.get(session_id)
    assert state.address is None
    assert result.order_id is None
    assert not orders.created
    session_store.remove(session_id)


@pytest.mark.asyncio
async def test_model_failure_does_not_mutate_order() -> None:
    class BrokenModel:
        async def plan(self, context):
            raise ModelUnavailable("offline")

    agent, orders, _ = make_agent({})
    agent._model = BrokenModel()
    session_id = str(uuid4())
    result = await agent.handle(session_id, "вода")
    assert "не могу обработать заказ" in result.reply
    assert not result.cart
    assert not orders.created
    session_store.remove(session_id)
