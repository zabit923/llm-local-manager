from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import httpx

from src.application.agent.prompts import (
    build_order_extraction_prompt,
    build_order_reply_prompt,
)
from src.application.agent.constants import (
    BRANCHES,
    STAGE_ASK_ADDRESS,
    STAGE_ASK_BRANCH,
    STAGE_ASK_DELIVERY,
    STAGE_ASK_ORDER,
    STAGE_CONFIRM,
    STAGE_ITEM_ADDED,
    STAGE_UNAVAILABLE,
)
from src.application.logging import agent_log


@dataclass(frozen=True)
class ExtractedOrderItem:
    name: str
    quantity: int


class QwenOrderExtractor:
    def __init__(
        self, base_url: str | None = None, model: str | None = None
    ) -> None:
        self._base_url = (
            base_url or os.getenv("LLM_BASE_URL", "http://127.0.0.1:8000/v1")
        ).rstrip("/")
        self._model = model or os.getenv("LLM_MODEL", "Qwen/Qwen3-8B-AWQ")

    async def reply(
        self,
        customer_text: str,
        stage: str,
        cart: list[str],
        facts: dict[str, str],
        fallback: str,
    ) -> str:
        prompt = build_order_reply_prompt(
            customer_text,
            stage,
            cart,
            facts,
        )
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": "Bearer local"},
                    json={
                        "model": self._model,
                        "messages": [{"role": "user", "content": prompt}],
                        "chat_template_kwargs": {
                            "enable_thinking": False,
                        },
                        "temperature": 0.4,
                        "max_tokens": 256,
                    },
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                agent_log.model_response("reply", content)
                answer = re.sub(
                    r"<think>.*?</think>",
                    "",
                    content,
                    flags=re.DOTALL,
                ).strip()
                if "<think>" in answer:
                    answer = answer.split("<think>", 1)[0].strip()
                return (
                    answer
                    if self._is_valid_reply(stage, answer, customer_text)
                    else fallback
                )
        except (
            httpx.HTTPError,
            KeyError,
            TypeError,
            IndexError,
        ):
            return fallback

    @staticmethod
    def _is_valid_reply(
        stage: str,
        answer: str,
        customer_text: str,
    ) -> bool:
        lowered = answer.lower()
        if not answer:
            return False
        if stage == STAGE_ASK_BRANCH:
            customer_words = set(re.findall(r"[а-яё]+", customer_text.lower()))
            known_words = {branch.lower() for branch in BRANCHES}
            has_noise = any(
                word in lowered
                for word in customer_words - known_words
                if len(word) > 3
            )
            return not has_noise and any(
                branch.lower() in lowered for branch in BRANCHES
            )
        if stage == STAGE_ASK_DELIVERY:
            return "достав" in lowered or "самовывоз" in lowered
        if stage == STAGE_ASK_ADDRESS:
            return "адрес" in lowered
        if stage == STAGE_CONFIRM:
            return "подтверд" in lowered
        if stage == STAGE_ITEM_ADDED:
            return "точк" in lowered or "филиал" in lowered
        if stage == STAGE_ASK_ORDER:
            return any(word in lowered for word in ("заказ", "блюд", "напит"))
        if stage == STAGE_UNAVAILABLE:
            customer_words = set(re.findall(r"[а-яё]+", customer_text.lower()))
            has_item = any(
                word in lowered for word in customer_words if len(word) > 3
            )
            return has_item and ("налич" in lowered or "нет" in lowered)
        return True

    async def extract(self, text: str) -> ExtractedOrderItem | None:
        prompt = build_order_extraction_prompt(text)
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": "Bearer local"},
                    json={
                        "model": self._model,
                        "messages": [{"role": "user", "content": prompt}],
                        "chat_template_kwargs": {
                            "enable_thinking": False,
                        },
                        "temperature": 0,
                        "max_tokens": 80,
                    },
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                agent_log.model_response("extract", content)
                match = re.search(r"\{.*\}", content, re.DOTALL)
                if not match:
                    return None
                data = json.loads(match.group(0))
                name = data.get("item")
                return (
                    ExtractedOrderItem(
                        str(name), max(1, int(data.get("quantity", 1)))
                    )
                    if name
                    else None
                )
        except (
            httpx.HTTPError,
            KeyError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):
            return None
