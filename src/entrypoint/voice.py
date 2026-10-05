import asyncio
import logging
import os
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from silero_vad import VADIterator, load_silero_vad

from src.application.logging.voice import voice_log
from src.application.voice import constants
from src.application.voice.errors import InvalidVoicePacket
from src.application.voice.service import VoiceCall
from src.infrastructure.implementation.speech.agent_client import (
    HttpOrderingAgent,
)
from src.infrastructure.implementation.speech.models import SpeechModels
from src.infrastructure.implementation.speech.vad import SileroDetector


class VoiceStart(BaseModel):

    session_id: str = Field(min_length=1, max_length=100)


async def conversation(socket: WebSocket, models: SpeechModels) -> None:
    await socket.accept()
    session_id = ""
    try:
        start = VoiceStart.model_validate(await socket.receive_json())
        session_id = start.session_id
        vad_model = await asyncio.to_thread(load_silero_vad)
        detector = SileroDetector(
            VADIterator(
                vad_model,
                threshold=constants.VAD_THRESHOLD,
                sampling_rate=constants.SAMPLE_RATE,
                min_silence_duration_ms=constants.VAD_SILENCE_MS,
                speech_pad_ms=constants.VAD_SPEECH_PAD_MS,
            )
        )
        async with httpx.AsyncClient(
            base_url=os.getenv(
                constants.BACKEND_URL_ENV,
                constants.DEFAULT_BACKEND_URL,
            ),
            timeout=constants.BACKEND_TIMEOUT_SECONDS,
        ) as client:
            call = VoiceCall(
                socket, models, detector, HttpOrderingAgent(client)
            )
            await call.run(session_id)
    except WebSocketDisconnect:
        pass
    except InvalidVoicePacket:
        await _safe_close(socket, 1003)
    except (httpx.HTTPError, RuntimeError, ValueError, OSError):
        voice_log.failed(session_id)
        try:
            await socket.send_json(
                {
                    "type": "error",
                    "message": constants.CALL_FAILED_MESSAGE,
                }
            )
        except (RuntimeError, WebSocketDisconnect):
            pass
        await _safe_close(socket, 1011)
    finally:
        voice_log.disconnected(session_id)


async def _safe_close(socket: WebSocket, code: int) -> None:
    try:
        await socket.close(code=code)
    except (RuntimeError, WebSocketDisconnect):
        pass


def create_voice_app(models: SpeechModels | None = None) -> FastAPI:
    speech_models = models if models is not None else SpeechModels()

    @asynccontextmanager
    async def lifespan(_app):
        await asyncio.to_thread(speech_models.load)
        yield

    app = FastAPI(lifespan=lifespan)
    app.state.speech_models = speech_models

    @app.get("/health")
    async def health():
        return {"ready": speech_models.ready}

    @app.websocket("/ws")
    async def voice_socket(socket: WebSocket):
        await conversation(socket, speech_models)

    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format=constants.LOG_FORMAT)
    uvicorn.run(
        create_voice_app(),
        host=constants.VOICE_HOST,
        port=constants.VOICE_PORT,
    )


if __name__ == "__main__":
    main()
