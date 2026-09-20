from __future__ import annotations

ORDER_EXTRACTION_INSTRUCTION = (
    "Ты извлекаешь заказ из русской фразы клиента ресторана. "
    'Верни JSON: {"item": string|null, "quantity": integer}. '
    "Если блюда или напитка нет в фразе, item должен быть null."
)


def build_order_extraction_prompt(text: str) -> str:
    return f"{ORDER_EXTRACTION_INSTRUCTION} Фраза клиента: {text}"
