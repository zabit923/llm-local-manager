import logging

from src.application.logging import messages


class VoiceLog:

    def __init__(self) -> None:
        self._logger = logging.getLogger(messages.VOICE_LOGGER)

    def connected(self, session_id: str) -> None:
        self._logger.info(messages.VOICE_CONNECTED, session_id)

    def disconnected(self, session_id: str) -> None:
        self._logger.info(messages.VOICE_DISCONNECTED, session_id)

    def failed(self, session_id: str) -> None:
        self._logger.exception(messages.VOICE_FAILED, session_id)

    def speech_started(self, session_id: str) -> None:
        self._logger.info(messages.SPEECH_STARTED, session_id)

    def speech_ended(
        self, session_id: str, seconds: float, reason: str
    ) -> None:
        self._logger.info(messages.SPEECH_ENDED, session_id, seconds, reason)

    def transcribed(self, session_id: str, seconds: float, text: str) -> None:
        self._logger.info(messages.TRANSCRIBED, session_id, seconds, text)

    def agent_replied(self, session_id: str, seconds: float, payload: dict):
        self._logger.info(
            messages.AGENT_REPLIED,
            session_id,
            seconds,
            payload["reply"],
            payload.get("order_id"),
        )

    def synthesized(self, session_id: str, seconds: float, size: int) -> None:
        self._logger.info(messages.SYNTHESIZED, session_id, seconds, size)


voice_log = VoiceLog()
