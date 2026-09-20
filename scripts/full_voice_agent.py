"""Полный локальный flow: VAD -> STT -> Qwen -> Order API -> TTS.

Требует:
  1. vLLM на 127.0.0.1:8000;
  2. backend с PostgreSQL на 127.0.0.1:8088;
  3. хотя бы одно блюдо или напиток в меню.

Запуск из корня проекта:
    poetry run python scripts/full_voice_agent.py
"""

from __future__ import annotations

import json
import os
import re
from difflib import get_close_matches

import httpx

from voice_loop import load_models, record_turn, speak, transcribe


ORDER_API_URL = os.getenv(
    "ORDER_API_URL",
    "http://127.0.0.1:8088/api/v1/staff",
).rstrip("/")

NUMBER_WORDS = {
    "ноль": 0,
    "один": 1,
    "одна": 1,
    "одно": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
}


def normalize(value: str) -> str:
    return re.sub(r"[^а-яёa-z0-9 ]", " ", value.casefold()).strip()


def extract_number(text: str) -> int | None:
    for word in normalize(text).split():
        if word.isdigit():
            number = int(word)
            if number > 0:
                return number
        if word in NUMBER_WORDS and NUMBER_WORDS[word] > 0:
            return NUMBER_WORDS[word]
    return None


class FullVoiceAgent:
    def __init__(self, client: httpx.Client, model_name: str) -> None:
        self.client = client
        self.model_name = model_name
        self.order_id: str | None = None
        self.menu: list[dict] = []
        self.messages: list[dict[str, str]] = []

    def load_menu(self) -> None:
        dishes = self.client.get("/dishes/").raise_for_status()
        drinks = self.client.get("/drinks/").raise_for_status()
        self.menu = [
            {**item, "item_type": "dish"}
            for item in dishes.json().get("dishes", [])
            if item.get("is_available", True)
        ] + [
            {**item, "item_type": "drink"}
            for item in drinks.json().get("drinks", [])
            if item.get("is_available", True)
        ]
        if not self.menu:
            raise RuntimeError(
                "Меню пустое. Добавь блюда или напитки через http://127.0.0.1:8088/docs"
            )

    def start(self) -> None:
        menu_text = "; ".join(
            f"{item['item_type']}: {item['name']}"
            for item in self.menu
        )
        self.messages = [
            {
                "role": "system",
                "content": (
                    "Ты голосовой менеджер ресторана. Отвечай коротко и по-русски. "
                    "Твоя задача — определить намерение клиента и вернуть только JSON "
                    "с полями intent, item_type, item_name, quantity, reply. "
                    "intent может быть add_item, confirm, greeting или question. "
                    "Если клиент уже назвал количество, не спрашивай его повторно. "
                    f"Доступное меню: {menu_text}"
                ),
            }
        ]

    def classify(self, user_text: str) -> dict:
        self.messages.append({"role": "user", "content": user_text})
        response = self.client.post(
            "http://127.0.0.1:8000/v1/chat/completions",
            json={
                "model": self.model_name,
                "messages": self.messages,
                "temperature": 0,
                "max_tokens": 160,
                "response_format": {"type": "json_object"},
                "chat_template_kwargs": {"enable_thinking": False},
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"].get("content", "{}")
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            result = {"intent": "question", "reply": content}
        return result

    def resolve_item(self, item_name: str | None, item_type: str | None) -> dict | None:
        if not item_name:
            return None
        candidates = [
            item for item in self.menu
            if not item_type or item["item_type"] == item_type
        ]
        names = [normalize(item["name"]) for item in candidates]
        query = normalize(item_name)
        for item, name in zip(candidates, names):
            if query == name or query in name or name in query:
                return item
        match = get_close_matches(query, names, n=1, cutoff=0.45)
        if match:
            return candidates[names.index(match[0])]
        return None

    def add_item(self, item: dict, quantity: int) -> dict:
        if self.order_id is None:
            response = self.client.post(
                "/orders/",
                json={
                    "branch": "Ермошкина",
                    "delivery_type": "pickup",
                    "payment_method": "cash",
                    "items": [
                        {
                            f"{item['item_type']}_id": item["id"],
                            "quantity": quantity,
                        }
                    ],
                },
            )
        else:
            response = self.client.post(
                f"/orders/{self.order_id}/"
                f"{'dishes' if item['item_type'] == 'dish' else 'drinks'}/{item['id']}",
                params={"quantity": quantity},
            )
        response.raise_for_status()
        order = response.json()
        self.order_id = order["id"]
        return order

    def reply(self, user_text: str) -> str:
        decision = self.classify(user_text)
        intent = decision.get("intent", "question")

        if intent == "add_item":
            item = self.resolve_item(
                decision.get("item_name"),
                decision.get("item_type"),
            )
            quantity = decision.get("quantity") or extract_number(user_text) or 1
            if item is None:
                answer = "Я не нашла такую позицию в меню. Назовите блюдо или напиток ещё раз."
            else:
                order = self.add_item(item, max(1, int(quantity)))
                total = order["total_price_minor"] / 100
                answer = (
                    f"Добавила {quantity} × {item['name']}. "
                    f"Сумма заказа — {total:.2f} рубля. Что добавить ещё?"
                )
        elif intent == "confirm" and self.order_id is not None:
            response = self.client.post(f"/orders/{self.order_id}/confirm")
            response.raise_for_status()
            answer = "Заказ подтверждён. Спасибо!"
        else:
            answer = decision.get("reply") or "Уточните, пожалуйста, что вы хотите заказать."

        self.messages.append({"role": "assistant", "content": answer})
        return answer


def main() -> None:
    asr, vad_model, tts = load_models()
    with httpx.Client(base_url=ORDER_API_URL, timeout=90.0) as order_client:
        agent = FullVoiceAgent(order_client, "Qwen/Qwen3-8B-AWQ")
        agent.load_menu()
        agent.start()
        speak(tts, "Здравствуйте. Чем могу помочь с заказом?")
        print("\nПолный голосовой flow запущен. Для остановки нажми Ctrl+C.")

        while True:
            audio_path = record_turn(vad_model)
            if audio_path is None:
                continue
            user_text = transcribe(asr, audio_path)
            if not user_text:
                speak(tts, "Я вас не расслышала. Повторите, пожалуйста.")
                continue
            print(f"КЛИЕНТ: {user_text}")
            answer = agent.reply(user_text)
            print(f"АГЕНТ: {answer}")
            speak(tts, answer)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nРазговор завершён.")
