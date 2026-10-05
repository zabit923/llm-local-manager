from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.application.logging import messages

if TYPE_CHECKING:
    from src.application.agent.conversation.state import ConversationState


class AgentLog:

    def __init__(self) -> None:
        self._logger = logging.getLogger(messages.AGENT_LOGGER)

    def input(
        self,
        session_id: str,
        text: str,
        state: ConversationState,
    ) -> None:
        self._logger.info(
            messages.AGENT_INPUT,
            session_id,
            text,
            len(state.lines),
            state.branch,
            state.delivery_type,
            bool(state.address),
        )

    def completed(self, session_id: str, order_id: Any) -> None:
        self._logger.info(messages.AGENT_COMPLETED, session_id, order_id)

    def extraction(self, session_id: str, result: Any) -> None:
        self._logger.debug(messages.AGENT_PLAN, session_id, result)

    def actions(self, session_id: str, events: Any) -> None:
        self._logger.info(messages.AGENT_ACTIONS, session_id, events)

    def reply(self, session_id: str, stage: str, text: str) -> None:
        self._logger.debug(messages.AGENT_REPLY, session_id, stage, text)

    def model_response(self, operation: str, text: str) -> None:
        self._logger.debug(messages.MODEL_RESPONSE, operation, text)


class SocketLog:

    def __init__(self) -> None:
        self._logger = logging.getLogger(messages.SOCKET_LOGGER)

    def connected(self, client: Any) -> None:
        self._logger.info(messages.SOCKET_CONNECTED, client)

    def received(self, data: Any) -> None:
        self._logger.info(messages.SOCKET_RECEIVED, data)

    def sent(self, data: Any) -> None:
        self._logger.info(messages.SOCKET_SENT, data)

    def disconnected(self, client: Any) -> None:
        self._logger.info(messages.SOCKET_DISCONNECTED, client)

    def failed(self, client: Any) -> None:
        self._logger.exception(messages.SOCKET_FAILED, client)


agent_log = AgentLog()
socket_log = SocketLog()
