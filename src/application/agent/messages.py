from __future__ import annotations

from uuid import UUID

from src.application.agent.constants import BRANCHES

DELIVERY_PROMPT = "Это будет доставка или самовывоз?"
ADDRESS_PROMPT = "Назовите адрес доставки."
ORDER_START_PROMPT = "Что хотите заказать? Я проверю наличие блюд и напитков."


def branch_prompt() -> str:
    return "На какую точку оформить заказ? Доступны: " f"{', '.join(BRANCHES)}."


def unavailable_message(name: str) -> str:
    return (
        f"К сожалению, «{name}» сейчас нет в наличии. "
        "Выберите другое блюдо или напиток."
    )


def item_added_message(name: str, quantity: int) -> str:
    return f"Записала: {name} × {quantity}. " "На какую точку оформить заказ?"


def item_label(name: str, quantity: int) -> str:
    return f"{name} × {quantity}"


def order_accepted_message(order_id: UUID) -> str:
    return f"Заказ принят. Номер заказа: {order_id}. Спасибо!"


def confirm_message(labels: list[str], branch: str, delivery_label: str) -> str:
    return (
        f"Подтвердить заказ: {', '.join(labels)}; "
        f"точка {branch}; {delivery_label}?"
    )
