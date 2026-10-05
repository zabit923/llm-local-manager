"""Audio protocol checks without GPU inference or external servers."""

import asyncio
import io
import json

import httpx
import numpy as np
import pytest
import soundfile as sf

from src.entrypoint import voice as voice_server

models = voice_server.create_voice_app().state.speech_models


class FrameVad:
    """Deterministic speech boundary for testing frame buffering."""

    def __init__(self, *_args, **_kwargs):
        self.frames = 0

    def reset_states(self):
        self.frames = 0

    def __call__(self, _frame):
        self.frames += 1
        if self.frames == 2:
            return {"start": 0}
        if self.frames == 8:
            return {"end": 4096}
        return None


def setup_gateway(monkeypatch):
    requests = []
    transcriptions = []

    async def inline_inference(function, *args, **kwargs):
        return function(*args, **kwargs)

    # Protocol tests stub inference; executor behavior is not under test.
    monkeypatch.setattr(voice_server.asyncio, "to_thread", inline_inference)
    output = io.BytesIO()
    sf.write(output, np.zeros(2400), 24000, format="WAV")
    monkeypatch.setattr(models, "load", lambda: None)
    monkeypatch.setattr(
        models,
        "synthesize",
        lambda text: output.getvalue(),
    )

    def transcribe(samples):
        transcriptions.append(samples)
        return "одну воду"

    monkeypatch.setattr(models, "transcribe", transcribe)
    monkeypatch.setattr(voice_server, "load_silero_vad", lambda **kw: None)
    monkeypatch.setattr(voice_server, "VADIterator", FrameVad)

    def backend(request):
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(
            200,
            json={
                "session_id": body["session_id"],
                "reply": (
                    "Здравствуйте" if len(requests) == 1 else "Добавила воду"
                ),
                "cart": [],
                "order_id": None,
            },
        )

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        voice_server.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            **kwargs,
            transport=httpx.MockTransport(backend),
        ),
    )
    return requests, transcriptions


class MemorySocket:
    """ASGI-like socket queues without network or thread portals."""

    def __init__(self, packets):
        self.packets = iter(packets)
        self.sent = []

    async def accept(self):
        pass

    async def receive_json(self):
        return {"session_id": "audio-test"}

    async def receive(self):
        packet = next(self.packets, {"type": "websocket.disconnect"})
        return {"type": "websocket.receive", **packet}

    async def send_json(self, payload):
        self.sent.append(payload)

    async def send_bytes(self, payload):
        self.sent.append(payload)

    async def close(self, code):
        self.sent.append({"closed": code})


def read_reply(events):
    assert next(events)["state"] == "thinking"
    reply = next(events)
    assert reply["type"] == "reply"
    assert next(events)["state"] == "speaking"
    assert next(events).startswith(b"RIFF")
    return reply


@pytest.mark.asyncio
async def test_pcm_boundaries_and_local_voice_reply(monkeypatch):
    requests, transcriptions = setup_gateway(monkeypatch)
    pcm = np.full(4096, 8192, dtype="<i2").tobytes()
    packets = [{"text": json.dumps({"type": "playback_done"})}]
    packets.extend(
        {"bytes": pcm[offset : offset + 768]}
        for offset in range(0, len(pcm), 768)
    )
    ws = MemorySocket(packets)
    await asyncio.wait_for(voice_server.conversation(ws, models), timeout=5)
    events = iter(ws.sent)
    read_reply(events)
    assert next(events)["state"] == "listening"
    assert next(events)["state"] == "user"
    assert next(events)["state"] == "transcribing"
    assert next(events)["text"] == "одну воду"
    read_reply(events)
    assert [request["text"] for request in requests] == [
        "Здравствуйте",
        "одну воду",
    ]
    assert len(transcriptions) == 1
    assert len(transcriptions[0]) == 4096
    assert np.allclose(transcriptions[0], 0.25)


@pytest.mark.asyncio
async def test_playback_audio_is_not_recognized_as_customer(monkeypatch):
    requests, transcriptions = setup_gateway(monkeypatch)
    ws = MemorySocket([{"bytes": np.zeros(8192, dtype="<i2").tobytes()}])
    await asyncio.wait_for(voice_server.conversation(ws, models), timeout=5)
    read_reply(iter(ws.sent))
    assert len(requests) == 1
    assert not transcriptions


@pytest.mark.asyncio
async def test_invalid_pcm_closes_call(monkeypatch):
    setup_gateway(monkeypatch)
    ws = MemorySocket(
        [
            {"text": json.dumps({"type": "playback_done"})},
            {"bytes": b"odd"},
        ]
    )
    await asyncio.wait_for(voice_server.conversation(ws, models), timeout=5)
    assert ws.sent[-1] == {"closed": 1003}


@pytest.mark.asyncio
async def test_duplicate_playback_done_does_not_reset_speech(monkeypatch):
    _, transcriptions = setup_gateway(monkeypatch)
    control = {"text": json.dumps({"type": "playback_done"})}
    pcm = np.full(512, 8192, dtype="<i2").tobytes()
    ws = MemorySocket(
        [
            control,
            *[{"bytes": pcm} for _ in range(3)],
            control,
            *[{"bytes": pcm} for _ in range(5)],
        ]
    )
    await asyncio.wait_for(voice_server.conversation(ws, models), timeout=5)
    assert len(transcriptions) == 1
    assert len(transcriptions[0]) == 4096
    listening = [
        event
        for event in ws.sent
        if isinstance(event, dict) and event.get("state") == "listening"
    ]
    assert len(listening) == 1


@pytest.mark.asyncio
async def test_non_object_control_closes_call(monkeypatch):
    setup_gateway(monkeypatch)
    ws = MemorySocket([{"text": "[]"}])
    await asyncio.wait_for(voice_server.conversation(ws, models), timeout=5)
    assert ws.sent[-1] == {"closed": 1003}
