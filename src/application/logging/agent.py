from __future__ import annotations

import logging
from typing import Any


class AgentLog:
    def __init__(self) -> None:
        self._logger = logging.getLogger("src.application.agent")

    def input(
        self,
        session_id: str,
        text: str,
        items: int,
        branch: str | None,
        delivery: Any,
        has_address: bool,
    ) -> None:
        self._logger.info(
            "Agent input: session=%s text=%r items=%d branch=%s "
            "delivery=%s address=%s",
            session_id,
            text,
            items,
            branch,
            delivery,
            has_address,
        )

    def branch_parsed(self, session_id: str, branch: str | None) -> None:
        self._logger.debug(
            "Agent branch parsed: session=%s branch=%s",
            session_id,
            branch,
        )

    def delivery_parsed(self, session_id: str, delivery: Any) -> None:
        self._logger.debug(
            "Agent delivery parsed: session=%s delivery=%s",
            session_id,
            delivery,
        )

    def address_saved(self, session_id: str) -> None:
        self._logger.debug("Agent address saved: session=%s", session_id)

    def confirms(self, session_id: str) -> None:
        self._logger.info("Agent confirms order: session=%s", session_id)

    def completed(self, session_id: str, order_id: Any) -> None:
        self._logger.info(
            "Agent order completed: session=%s order_id=%s",
            session_id,
            order_id,
        )

    def extraction(self, session_id: str, result: Any) -> None:
        self._logger.debug(
            "Agent extraction: session=%s result=%s",
            session_id,
            result,
        )

    def catalog_match(self, session_id: str, item: str, match: Any) -> None:
        self._logger.debug(
            "Agent catalog match: session=%s item=%r match=%s",
            session_id,
            item,
            match,
        )

    def item_added(self, session_id: str, item: str, quantity: int) -> None:
        self._logger.info(
            "Agent item added: session=%s item=%s quantity=%d",
            session_id,
            item,
            quantity,
        )


class SocketLog:
    """Structured log messages for the agent WebSocket."""

    def __init__(self) -> None:
        self._logger = logging.getLogger(
            "src.presentation.api_v1.views.public.agent"
        )

    def connected(self, client: Any) -> None:
        self._logger.info("Agent websocket connected: client=%s", client)

    def received(self, data: Any) -> None:
        self._logger.info("Agent websocket received: data=%s", data)

    def sent(self, data: Any) -> None:
        self._logger.info("Agent websocket sent: data=%s", data)

    def disconnected(self, client: Any) -> None:
        self._logger.info("Agent websocket disconnected: client=%s", client)

    def failed(self, client: Any) -> None:
        self._logger.exception("Agent websocket failed: client=%s", client)


agent_log = AgentLog()
socket_log = SocketLog()
