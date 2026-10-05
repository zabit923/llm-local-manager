from __future__ import annotations

import json
import os
import re

import httpx

from src.application.agent.config.prompts import (
    build_planner_messages,
    build_reply_messages,
)
from src.application.agent.contracts.errors import ModelUnavailable
from src.application.logging import agent_log
from src.infrastructure.implementation.llm import constants


class QwenAgentModel:
    def __init__(
        self, base_url: str | None = None, model: str | None = None
    ) -> None:
        self._base_url = (
            base_url
            or os.getenv(constants.BASE_URL_ENV, constants.DEFAULT_BASE_URL)
        ).rstrip("/")
        self._model = model or os.getenv(
            constants.MODEL_ENV, constants.DEFAULT_MODEL
        )

    async def _chat(
        self,
        messages: list[dict[str, str]],
        operation: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        try:
            async with httpx.AsyncClient(
                timeout=constants.REQUEST_TIMEOUT_SECONDS
            ) as client:
                response = await client.post(
                    self._base_url + constants.CHAT_COMPLETIONS_PATH,
                    headers={"Authorization": constants.LOCAL_AUTHORIZATION},
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
                    raise ModelUnavailable(constants.EMPTY_RESPONSE_ERROR)
        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ) as exc:
            raise ModelUnavailable(str(exc)) from exc
        agent_log.model_response(operation, content)
        content = re.sub(
            constants.THINK_PATTERN, "", content, flags=re.DOTALL
        ).strip()
        if "<think>" in content:
            raise ModelUnavailable(constants.UNFINISHED_REASONING_ERROR)
        return content

    async def plan(self, context: dict) -> dict:
        messages = build_planner_messages(context)
        for attempt in range(constants.MAX_PLAN_ATTEMPTS):
            content = await self._chat(
                messages,
                "plan",
                temperature=constants.PLAN_TEMPERATURE,
                max_tokens=constants.PLAN_TOKEN_LIMIT,
            )
            match = re.search(constants.JSON_OBJECT_PATTERN, content, re.DOTALL)
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
                        "content": constants.RETRY_PLAN_INSTRUCTION,
                    }
                )
        raise ModelUnavailable(constants.INVALID_PLAN_ERROR)

    async def respond(self, context: dict) -> str:
        content = await self._chat(
            build_reply_messages(context),
            "reply",
            temperature=constants.REPLY_TEMPERATURE,
            max_tokens=constants.REPLY_TOKEN_LIMIT,
        )
        if not content or len(content) > constants.MAX_REPLY_CHARACTERS:
            raise ModelUnavailable(constants.INVALID_REPLY_ERROR)
        return content
