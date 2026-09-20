from __future__ import annotations

from src.application.agent.constants import BRANCHES

DELIVERY_PROMPT = "Это будет доставка или самовывоз?"
ADDRESS_PROMPT = "Назовите адрес доставки."
NO_ORDER_PROMPT = "Хорошо. Что хотите заказать?"


def branch_prompt() -> str:
    return "На какую точку оформить заказ? Доступны: " f"{', '.join(BRANCHES)}."


def unavailable_message(name: str) -> str:
    return (
        f"К сожалению, «{name}» сейчас нет в наличии. "
        "Выберите другое блюдо или напиток."
    )


def menu_message(names: list[str]) -> str:
    return f"В меню сейчас: {', '.join(names)}. Что хотите заказать?"


def not_found_message(name: str, names: list[str]) -> str:
    return (
        f"К сожалению, «{name}» нет в меню. "
        f"Могу предложить: {', '.join(names)}."
    )


def item_added_message(name: str, quantity: int) -> str:
    return f"Записала: {quantity} {name}. На какую точку оформить заказ?"


def item_label(name: str, quantity: int) -> str:
    return f"{quantity} {name}"


def order_created_message(total_price_minor: int) -> str:
    price = total_price_minor / 100
    return f"Заказ создан. Сумма заказа: {price:.2f} ₽."
