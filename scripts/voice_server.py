"""Local audio gateway. Run: poetry run python scripts/voice_server.py."""

import asyncio
import io
import json
import logging
import os
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import numpy as np
import soundfile as sf
import torch
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from silero_vad import VADIterator, load_silero_vad
from transformers import pipeline

logger = logging.getLogger("voice")
RATE = 16000
FRAME = 512
BACKEND = os.getenv("VOICE_BACKEND_URL", "http://127.0.0.1:8088")


class SpeechModels:
    """Load once, serialize inference on the shared GPU and CPU models."""

    def __init__(self):
        self.lock = asyncio.Lock()
        self.asr = None
        self.tts = None

    def load(self):
        torch.set_num_threads(4)
        device = os.getenv("VOICE_ASR_DEVICE", "cuda:0")
        logger.info("Loading Parakeet on %s", device)
        self.asr = pipeline(
            "automatic-speech-recognition",
            model="nvidia/parakeet-tdt-0.6b-v3",
            device=device,
            dtype=torch.float16 if "cuda" in device else torch.float32,
        )
        cached = (
            Path(torch.hub.get_dir()) / "snakers4_silero-models_master"
            / "src/silero/model/v5_ru.pt"
        )
        model_path = Path(os.getenv(
            "VOICE_TTS_PATH", str(cached if cached.exists() else (
                Path(__file__).resolve().parents[1]
                / ".voice-models/v5_ru.pt"
            )),
        ))
        if not model_path.exists():
            model_path.parent.mkdir(parents=True, exist_ok=True)
            torch.hub.download_url_to_file(
                "https://models.silero.ai/models/tts/ru/v5_ru.pt",
                str(model_path),
            )
        # Load the packaged model without importing the hub's `src` package.
        self.tts = torch.package.PackageImporter(str(model_path)).load_pickle(
            "tts_models", "model",
        )
        self.tts.to("cpu")
        logger.info("Parakeet and Silero TTS v5_ru ready")

    def transcribe(self, samples):
        result = self.asr(
            {"raw": samples, "sampling_rate": RATE},
            generate_kwargs={"max_new_tokens": 256},
        )
        return result["text"].strip()

    def synthesize(self, text):
        with torch.inference_mode():
            audio = self.tts.apply_tts(
                text=text, speaker="xenia", sample_rate=24000,
            ).detach().cpu().numpy()
        output = io.BytesIO()
        sf.write(output, audio, 24000, format="WAV", subtype="PCM_16")
        return output.getvalue()


models = SpeechModels()


@asynccontextmanager
async def lifespan(_app):
    await asyncio.to_thread(models.load)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"ready": models.asr is not None and models.tts is not None}


async def answer(ws, client, session_id, text):
    began = time.monotonic()
    await ws.send_json({"type": "state", "state": "thinking"})
    response = await client.post(
        "/api/v1/pub/agent/message",
        json={"session_id": session_id, "text": text},
    )
    response.raise_for_status()
    payload = response.json()
    logger.info(
        "Agent: session=%s seconds=%.2f reply=%r order_id=%s",
        session_id, time.monotonic() - began,
        payload["reply"], payload.get("order_id"),
    )
    await ws.send_json({"type": "reply", **payload})
    began = time.monotonic()
    async with models.lock:
        audio = await asyncio.to_thread(models.synthesize, payload["reply"])
    await ws.send_json({"type": "state", "state": "speaking"})
    await ws.send_bytes(audio)
    logger.info(
        "TTS: session=%s seconds=%.2f audio_bytes=%d",
        session_id, time.monotonic() - began, len(audio),
    )


@app.websocket("/ws")
async def conversation(ws: WebSocket):
    await ws.accept()
    session_id = "unknown"
    try:
        start = await ws.receive_json()
        session_id = start["session_id"]
        logger.info("Voice connected: session=%s", session_id)
        vad_model = await asyncio.to_thread(load_silero_vad)
        vad = VADIterator(
            vad_model, threshold=0.6, sampling_rate=RATE,
            min_silence_duration_ms=750, speech_pad_ms=160,
        )
        pending = np.empty(0, dtype=np.float32)
        preroll = deque(maxlen=10)
        utterance = []
        recording = False
        listening = False
        async with httpx.AsyncClient(
            base_url=BACKEND, timeout=90,
        ) as client:
            await answer(ws, client, session_id, "Здравствуйте")
            while True:
                packet = await ws.receive()
                if packet["type"] == "websocket.disconnect":
                    break
                if packet.get("text"):
                    control = json.loads(packet["text"])
                    if not isinstance(control, dict):
                        await ws.close(code=1003)
                        break
                    if (
                        control.get("type") == "playback_done"
                        and not listening
                    ):
                        listening = True
                        vad.reset_states()
                        pending = np.empty(0, dtype=np.float32)
                        preroll.clear()
                        await ws.send_json({
                            "type": "state", "state": "listening",
                        })
                    continue
                raw = packet.get("bytes")
                if not listening or not raw:
                    continue
                if len(raw) % 2 or len(raw) > 32768:
                    await ws.close(code=1003)
                    break
                samples = np.frombuffer(raw, dtype="<i2").astype(
                    np.float32
                ) / 32768
                pending = np.concatenate((pending, samples))
                while len(pending) >= FRAME:
                    frame, pending = pending[:FRAME], pending[FRAME:]
                    event = vad(torch.from_numpy(frame))
                    if event and "start" in event and not recording:
                        logger.info(
                            "VAD speech started: session=%s", session_id,
                        )
                        recording = True
                        utterance = list(preroll)
                        await ws.send_json({
                            "type": "state", "state": "user",
                        })
                    if recording:
                        utterance.append(frame.copy())
                    preroll.append(frame.copy())
                    ended = event and "end" in event
                    if recording and (
                        ended or len(utterance) >= 938
                    ):
                        recording = False
                        listening = False
                        audio = np.concatenate(utterance)
                        logger.info(
                            "VAD speech ended: session=%s duration=%.2f "
                            "reason=%s",
                            session_id, len(audio) / RATE,
                            "silence" if ended else "length_limit",
                        )
                        utterance = []
                        await ws.send_json({
                            "type": "state", "state": "transcribing",
                        })
                        began = time.monotonic()
                        async with models.lock:
                            text = await asyncio.to_thread(
                                models.transcribe, audio,
                            )
                        logger.info(
                            "STT: session=%s seconds=%.2f text=%r",
                            session_id, time.monotonic() - began, text,
                        )
                        await ws.send_json({
                            "type": "transcript", "text": text,
                        })
                        if text:
                            await answer(ws, client, session_id, text)
                        else:
                            listening = True
                            vad.reset_states()
                            preroll.clear()
                            await ws.send_json({
                                "type": "state", "state": "listening",
                            })
                        pending = np.empty(0, dtype=np.float32)
                        break
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Voice call failed: session=%s", session_id)
        try:
            await ws.send_json({
                "type": "error",
                "message": "Не удалось обработать звук. Начните звонок заново.",
            })
            await ws.close(code=1011)
        except RuntimeError:
            pass
    finally:
        logger.info("Voice disconnected: session=%s", session_id)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    uvicorn.run(app, host="0.0.0.0", port=8001)
