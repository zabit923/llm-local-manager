from __future__ import annotations

from queue import Empty, Queue
from pathlib import Path
from time import monotonic

import httpx
import numpy as np
import sounddevice as sd
import soundfile as sf
import torch
from silero_vad import VADIterator, load_silero_vad
from transformers import pipeline


VLLM_BASE_URL = "http://127.0.0.1:8000/v1"
MODEL_NAME = "Qwen/Qwen3-8B-AWQ"

RESTAURANT_NAME = "Горы Гиро"
GREETING = "Здравствуйте. Горы гиро на Ермошкина, чем могу помочь?"

INPUT_SAMPLE_RATE = 16_000
OUTPUT_SAMPLE_RATE = 24_000
VAD_WINDOW_SAMPLES = 512
VAD_THRESHOLD = 0.5
END_OF_SPEECH_SILENCE_MS = 800
START_SPEECH_TIMEOUT_SECONDS = 20
MAX_UTTERANCE_SECONDS = 30
RECORDING_PATH = Path("voice_turn.wav")


def load_models():
    """Загружает STT на GPU, а VAD и TTS — на CPU один раз при старте."""
    print("Загружаю распознавание речи…")
    asr = pipeline(
        "automatic-speech-recognition",
        model="nvidia/parakeet-tdt-0.6b-v3",
        device="cuda:0",
        dtype=torch.float16,
    )
    asr.model.generation_config.max_new_tokens = 256

    print("Загружаю детектор речи…")
    vad_model = load_silero_vad()

    print("Загружаю голос агента…")
    torch.set_num_threads(4)
    tts, _ = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language="ru",
        speaker="v5_5_ru",
    )
    tts.to("cpu")

    return asr, vad_model, tts


def speak(tts, text: str) -> None:
    """Озвучивает текст и ждёт завершения воспроизведения."""
    print(f"АГЕНТ: {text}")
    audio = tts.apply_tts(
        text=text,
        speaker="xenia",
        sample_rate=OUTPUT_SAMPLE_RATE,
    ).numpy()
    sd.play(audio, samplerate=OUTPUT_SAMPLE_RATE)
    sd.wait()


def record_turn(vad_model: torch.nn.Module) -> Path | None:
    """Записывает речь до паузы; микрофон не активен во время TTS."""
    audio_queue: Queue[np.ndarray] = Queue()
    vad = VADIterator(
        vad_model,
        threshold=VAD_THRESHOLD,
        sampling_rate=INPUT_SAMPLE_RATE,
        min_silence_duration_ms=END_OF_SPEECH_SILENCE_MS,
    )
    vad.reset_states()

    def audio_callback(indata, frames, time_info, status) -> None:
        del frames, time_info
        if status:
            print(f"Аудио: {status}")
        audio_queue.put(indata[:, 0].copy())

    frames: list[np.ndarray] = []
    speech_started = False
    start_deadline = monotonic() + START_SPEECH_TIMEOUT_SECONDS

    print("\nСлушаю… Говори после сигнала агента.")
    with sd.InputStream(
        samplerate=INPUT_SAMPLE_RATE,
        blocksize=VAD_WINDOW_SAMPLES,
        channels=1,
        dtype="float32",
        callback=audio_callback,
    ):
        while True:
            if not speech_started and monotonic() >= start_deadline:
                print("Речь не обнаружена.")
                return None

            try:
                chunk = audio_queue.get(timeout=0.25)
            except Empty:
                continue

            event = vad(torch.from_numpy(chunk))
            if event and "start" in event:
                speech_started = True

            if speech_started:
                frames.append(chunk)
                duration = sum(len(frame) for frame in frames) / INPUT_SAMPLE_RATE
                if duration >= MAX_UTTERANCE_SECONDS:
                    print("Достигнута максимальная длина фразы.")
                    break
                if event and "end" in event:
                    break

    audio = np.concatenate(frames)
    sf.write(RECORDING_PATH, audio, INPUT_SAMPLE_RATE)
    return RECORDING_PATH


def transcribe(asr, audio_path: Path) -> str:
    result = asr(str(audio_path))
    return result["text"].strip()


def ask_agent(client: httpx.Client, messages: list[dict[str, str]]) -> str:
    response = client.post(
        "/chat/completions",
        json={
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 120,
            "chat_template_kwargs": {"enable_thinking": False},
        },
    )
    response.raise_for_status()

    message = response.json()["choices"][0]["message"]
    return (message.get("content") or message.get("reasoning_content") or "").strip()


def main() -> None:
    asr, vad_model, tts = load_models()

    with httpx.Client(base_url=VLLM_BASE_URL, timeout=90.0) as client:
        client.get("/models").raise_for_status()

        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    f"Ты голосовой менеджер {RESTAURANT_NAME}. "
                    "Отвечай по-русски, коротко, естественно и без рассуждений. "
                    "Не придумывай блюда и цены. Если клиент уже назвал количество, "
                    "не спрашивай его повторно. Если данных не хватает, задай один вопрос."
                ),
            },
            {"role": "assistant", "content": GREETING},
        ]

        speak(tts, GREETING)
        print("\nРазговор начат. Для остановки нажми Ctrl+C.")

        while True:
            audio_path = record_turn(vad_model)
            if audio_path is None:
                continue
            user_text = transcribe(asr, audio_path)

            if not user_text:
                speak(tts, "Я вас не расслышала. Повторите, пожалуйста.")
                continue

            print(f"КЛИЕНТ: {user_text}")
            messages.append({"role": "user", "content": user_text})

            answer = ask_agent(client, messages)
            if not answer:
                answer = "Извините, я не смогла сформировать ответ. Повторите, пожалуйста."

            messages.append({"role": "assistant", "content": answer})
            speak(tts, answer)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nРазговор завершён.")
