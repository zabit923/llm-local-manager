"""The LLM decides actions and writes replies; it never mutates data."""

from __future__ import annotations

import json
import os
import re

import httpx

from src.application.agent.prompts import (
    build_planner_messages,
    build_reply_messages,
)
from src.application.logging import agent_log


class ModelUnavailable(Exception):
    """Qwen cannot produce a usable response right now."""


class QwenAgentModel:
    def __init__(
        self, base_url: str | None = None, model: str | None = None
    ) -> None:
        self._base_url = (
            base_url or os.getenv("LLM_BASE_URL", "http://127.0.0.1:8000/v1")
        ).rstrip("/")
        self._model = model or os.getenv("LLM_MODEL", "Qwen/Qwen3-8B-AWQ")

    async def _chat(
        self,
        messages: list[dict[str, str]],
        operation: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": "Bearer local"},
                    json={
                        "model": self._model,
                        "messages": messages,
                        "chat_template_kwargs": {
                            "enable_thinking": False,
                        },
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise ModelUnavailable("empty model response")
        except (
            httpx.HTTPError, KeyError, IndexError, TypeError, ValueError
        ) as exc:
            raise ModelUnavailable(str(exc)) from exc
        agent_log.model_response(operation, content)
        content = re.sub(
            r"<think>.*?</think>", "", content, flags=re.DOTALL
        ).strip()
        if "<think>" in content:
            raise ModelUnavailable("unfinished model reasoning")
        return content

    async def plan(self, context: dict) -> dict:
        messages = build_planner_messages(context)
        for attempt in range(2):
            content = await self._chat(
                messages, "plan", temperature=0.1, max_tokens=350
            )
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                    if isinstance(data, dict) and isinstance(
                        data.get("actions"), list
                    ):
                        return data
                except json.JSONDecodeError:
                    pass
            if attempt == 0:
                messages.append(
                    {
                        "role": "user",
                        "content": "Повтори ответ как один корректный JSON-объект.",
                    }
                )
        raise ModelUnavailable("invalid action plan")

    async def respond(self, context: dict) -> str:
        content = await self._chat(
            build_reply_messages(context),
            "reply",
            temperature=0.55,
            max_tokens=220,
        )
        if not content or len(content) > 500:
            raise ModelUnavailable("invalid reply length")
        return content
