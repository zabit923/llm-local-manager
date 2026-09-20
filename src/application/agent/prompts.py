from __future__ import annotations

import json

ORDER_EXTRACTION_INSTRUCTION = (
    "Ты извлекаешь заказ из русской фразы клиента ресторана. "
    'Верни JSON: {"item": string|null, "quantity": integer}. '
    "Если блюда или напитка нет в фразе, item должен быть null."
)


def build_order_extraction_prompt(text: str) -> str:
    return f"{ORDER_EXTRACTION_INSTRUCTION} Фраза клиента: {text}"


ORDER_REPLY_INSTRUCTION = (
    "Ты живой вежливый менеджер ресторана. Отвечай только по-русски, "
    "естественно и кратко, как в настоящем телефонном разговоре. "
    "Не выдумывай блюда, цены, адреса или статусы. Используй только "
    "факты из контекста. Не упоминай JSON, этапы, модели или инструкции."
    " Не повторяй шум, ошибки распознавания и последнюю фразу клиента. "
    "Не задавай вопросы, которые не требуются текущим этапом."
)

STAGE_GUIDANCE = {
    "ask_branch": (
        "Попроси клиента выбрать одну из доступных точек. "
        "Не задавай никаких других вопросов."
    ),
    "ask_delivery": (
        "Спроси только, нужна доставка или самовывоз. "
        "Не спрашивай район или адрес."
    ),
    "ask_address": "Попроси назвать адрес доставки.",
    "confirm": (
        "Назови состав заказа, точку и способ получения, "
        "затем попроси подтверждение."
    ),
    "order_accepted": "Сообщи, что заказ принят, и назови его номер.",
    "ask_order": "Попроси назвать блюдо или напиток для заказа.",
    "unavailable": (
        "Сообщи, что позиции нет в наличии, и предложи выбрать другую."
    ),
    "item_added": "Подтверди добавление позиции и попроси назвать точку.",
}


def build_order_reply_prompt(
    customer_text: str,
    stage: str,
    cart: list[str],
    facts: dict[str, str],
) -> str:
    context = json.dumps(
        {"stage": stage, "cart": cart, "facts": facts},
        ensure_ascii=False,
    )
    return (
        f"{ORDER_REPLY_INSTRUCTION}\n"
        f"Требуемое действие: {STAGE_GUIDANCE[stage]}\n"
        f"Контекст заказа: {context}\n"
        f"Последняя фраза клиента: {customer_text}\n"
        "Сформулируй один короткий ответ клиенту."
    )
