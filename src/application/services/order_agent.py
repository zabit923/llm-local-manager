from __future__ import annotations

import re
import json
import os
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from uuid import UUID

import httpx

from src.application.schemas.agent import AgentMessageResponse
from src.application.schemas.orders import OrderCreate, OrderItemCreate
from src.application.use_cases.dishes import DishUseCases
from src.application.use_cases.drinks import DrinkUseCases
from src.application.use_cases.orders import OrderUseCases
from src.domain.models.choises.enum import DeliveryType


BRANCHES = ("Ермошкина", "Центральная")
NUMBER_WORDS = {
    "один": 1, "одна": 1, "одно": 1, "раз": 1,
    "два": 2, "две": 2, "пару": 2, "пара": 2,
    "три": 3, "четыре": 4, "пять": 5,
}


@dataclass
class _State:
    items: list[OrderItemCreate] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    branch: str | None = None
    delivery_type: DeliveryType | None = None
    address: str | None = None


_SESSIONS: dict[str, _State] = {}


class OrderAgent:
    """Small deterministic conversation state machine for the demo UI."""

    def __init__(self, dishes: DishUseCases, drinks: DrinkUseCases, orders: OrderUseCases) -> None:
        self._dishes = dishes
        self._drinks = drinks
        self._orders = orders

    @staticmethod
    def _quantity(text: str) -> int:
        match = re.search(r"\b([1-9]|[1-9][0-9])\b", text)
        if match:
            return int(match.group(1))
        lowered = text.lower()
        for word, value in NUMBER_WORDS.items():
            if re.search(rf"\b{word}\w*\b", lowered):
                return value
        return 1

    @staticmethod
    def _similar(text: str, name: str) -> float:
        text, name = text.lower(), name.lower()
        if name in text:
            return 1.0
        return SequenceMatcher(None, text, name).ratio()

    @staticmethod
    def _stem_words(value: str) -> set[str]:
        words = re.findall(r"[а-яёa-z]+", value.lower())
        suffixes = ("иями", "ами", "ого", "ему", "ов", "ый", "ая", "ое", "ые", "ых", "ом", "ем", "ам", "ах", "а", "ы", "и", "у", "ю", "е", "й")
        result = set()
        for word in words:
            for suffix in suffixes:
                if len(word) > len(suffix) + 2 and word.endswith(suffix):
                    word = word[: -len(suffix)]
                    break
            if len(word) >= 3:
                result.add(word)
        return result

    async def _find_item(self, text: str):
        dishes = [dish for dish in await self._dishes.list() if dish.is_available]
        drinks = [drink for drink in await self._drinks.list() if drink.is_available]
        candidates = [(dish, "dish") for dish in dishes] + [(drink, "drink") for drink in drinks]
        ranked = sorted(candidates, key=lambda pair: self._similar(text, pair[0].name), reverse=True)
        if ranked and self._similar(text, ranked[0][0].name) >= 0.38:
            return ranked[0]
        # Speech recognition often adds greetings or mangles the noun. Match
        # meaningful inflected words too ("острых" -> "остр").
        spoken_words = self._stem_words(text)
        token_ranked = sorted(
            candidates,
            key=lambda pair: len(spoken_words & self._stem_words(pair[0].name)),
            reverse=True,
        )
        if token_ranked and spoken_words & self._stem_words(token_ranked[0][0].name):
            return token_ranked[0]
        unavailable = [dish for dish in await self._dishes.list() if not dish.is_available]
        unavailable += [drink for drink in await self._drinks.list() if not drink.is_available]
        ranked_unavailable = sorted(unavailable, key=lambda item: self._similar(text, item.name), reverse=True)
        if ranked_unavailable and self._similar(text, ranked_unavailable[0].name) >= 0.45:
            return ranked_unavailable[0], "unavailable"
        return None

    async def _llm_item(self, text: str) -> tuple[str, int] | None:
        """Ask local Qwen to normalize a spoken order into name + quantity."""
        base_url = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/")
        model = os.getenv("LLM_MODEL", "Qwen/Qwen3-8B-AWQ")
        prompt = (
            "Ты извлекаешь заказ из русской фразы клиента ресторана. "
            "Верни только JSON без markdown: {\"item\": string|null, \"quantity\": integer}. "
            "Если блюда или напитка нет в фразе, item должен быть null. "
            f"Фраза клиента: {text}"
        )
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": "Bearer local"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0,
                        "max_tokens": 80,
                    },
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                match = re.search(r"\{.*\}", content, re.DOTALL)
                if not match:
                    return None
                data = json.loads(match.group(0))
                item = data.get("item")
                if not item:
                    return None
                return str(item), max(1, int(data.get("quantity", 1)))
        except (httpx.HTTPError, KeyError, ValueError, TypeError, json.JSONDecodeError):
            return None

    async def handle(self, session_id: str, text: str) -> AgentMessageResponse:
        state = _SESSIONS.setdefault(session_id, _State())
        lowered = text.lower().strip()

        if state.items and state.branch is None:
            state.branch = next((branch for branch in BRANCHES if branch.lower() in lowered), None)
            if state.branch is None:
                return AgentMessageResponse(session_id=session_id, reply=f"На какую точку оформить заказ? Доступны: {', '.join(BRANCHES)}.", cart=state.labels)

        if state.items and state.delivery_type is None:
            if "самовывоз" in lowered or "заберу" in lowered or "забрать" in lowered:
                state.delivery_type = DeliveryType.pickup
            elif "достав" in lowered:
                state.delivery_type = DeliveryType.delivery
            else:
                return AgentMessageResponse(session_id=session_id, reply="Это будет доставка или самовывоз?", cart=state.labels)

        if state.items and state.delivery_type is DeliveryType.delivery and state.address is None:
            if "адрес" not in lowered and len(text.split()) < 2:
                return AgentMessageResponse(session_id=session_id, reply="Назовите адрес доставки.", cart=state.labels)
            state.address = text.strip()

        if state.items and state.branch and state.delivery_type:
            if any(word in lowered for word in ("да", "подтверждаю", "оформляй", "подтвердить")):
                order = await self._orders.create(OrderCreate(
                    branch=state.branch,
                    delivery_type=state.delivery_type,
                    address=state.address,
                    items=state.items,
                ))
                order = await self._orders.confirm(order.id)
                _SESSIONS.pop(session_id, None)
                return AgentMessageResponse(session_id=session_id, reply=f"Заказ принят. Номер заказа: {order.id}. Спасибо!", order_id=order.id)
            return AgentMessageResponse(session_id=session_id, reply=f"Подтвердить заказ: {', '.join(state.labels)}; точка {state.branch}; {'доставка' if state.delivery_type is DeliveryType.delivery else 'самовывоз'}?", cart=state.labels)

        llm_item = await self._llm_item(text)
        item_text, quantity = llm_item if llm_item else (text, self._quantity(text))
        found = await self._find_item(item_text)
        if found is None:
            return AgentMessageResponse(session_id=session_id, reply="Что хотите заказать? Я проверю наличие блюд и напитков.", cart=state.labels)
        item, kind = found
        if kind == "unavailable":
            return AgentMessageResponse(session_id=session_id, reply=f"К сожалению, «{item.name}» сейчас нет в наличии. Выберите другое блюдо или напиток.", cart=state.labels)
        state.items.append(OrderItemCreate(**({"dish_id": item.id} if kind == "dish" else {"drink_id": item.id}), quantity=quantity))
        state.labels.append(f"{item.name} × {quantity}")
        return AgentMessageResponse(session_id=session_id, reply=f"Записала: {item.name} × {quantity}. На какую точку оформить заказ?", cart=state.labels)
