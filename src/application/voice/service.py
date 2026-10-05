import asyncio
import json
import time

from fastapi import WebSocket

from src.application.logging.voice import voice_log
from src.application.voice import constants
from src.application.voice.buffer import UtteranceBuffer
from src.application.voice.dto import SpeechEvent
from src.application.voice.errors import InvalidVoicePacket
from src.application.voice.ports import (
    OrderingAgent,
    SpeechDetector,
    SpeechInference,
)


class VoiceCall:

    def __init__(
        self,
        socket: WebSocket,
        models: SpeechInference,
        detector: SpeechDetector,
        agent: OrderingAgent,
    ) -> None:
        self._socket = socket
        self._models = models
        self._detector = detector
        self._agent = agent
        self._buffer = UtteranceBuffer(detector)
        self._listening = False
        self._session_id = ""

    async def run(self, session_id: str) -> None:
        self._session_id = session_id
        voice_log.connected(session_id)
        await self._answer(constants.INITIAL_GREETING)
        while True:
            packet = await self._socket.receive()
            if packet["type"] == "websocket.disconnect":
                return
            if packet.get("text"):
                await self._control(packet["text"])
            elif self._listening and packet.get("bytes"):
                await self._audio(packet["bytes"])

    async def _state(self, value: str) -> None:
        await self._socket.send_json({"type": "state", "state": value})

    async def _control(self, raw: str) -> None:
        try:
            control = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InvalidVoicePacket(constants.INVALID_CONTROL_MESSAGE) from exc
        if not isinstance(control, dict):
            raise InvalidVoicePacket(constants.INVALID_CONTROL_MESSAGE)
        if control.get("type") == "playback_done" and not self._listening:
            await self._listen()

    async def _listen(self) -> None:
        self._listening = True
        self._detector.reset_states()
        self._buffer.reset()
        await self._state("listening")

    async def _audio(self, raw: bytes) -> None:
        for event in self._buffer.feed(raw):
            if event.kind == "start":
                voice_log.speech_started(self._session_id)
                await self._state("user")
            else:
                await self._utterance(event)

    async def _utterance(self, event: SpeechEvent) -> None:
        self._listening = False
        voice_log.speech_ended(
            self._session_id,
            len(event.samples) / constants.SAMPLE_RATE,
            event.reason,
        )
        await self._state("transcribing")
        began = time.monotonic()
        async with self._models.lock:
            text = await asyncio.to_thread(
                self._models.transcribe,
                event.samples,
            )
        voice_log.transcribed(self._session_id, time.monotonic() - began, text)
        await self._socket.send_json({"type": "transcript", "text": text})
        if text:
            await self._answer(text)
        else:
            await self._listen()

    async def _answer(self, text: str) -> None:
        await self._state("thinking")
        began = time.monotonic()
        payload = await self._agent.message(self._session_id, text)
        voice_log.agent_replied(
            self._session_id,
            time.monotonic() - began,
            payload,
        )
        await self._socket.send_json({"type": "reply", **payload})
        began = time.monotonic()
        async with self._models.lock:
            audio = await asyncio.to_thread(
                self._models.synthesize,
                payload["reply"],
            )
        voice_log.synthesized(
            self._session_id,
            time.monotonic() - began,
            len(audio),
        )
        await self._state("speaking")
        await self._socket.send_bytes(audio)
