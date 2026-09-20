from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import httpx

from src.application.agent.prompts import build_order_extraction_prompt


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
