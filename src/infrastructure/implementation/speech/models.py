import asyncio
import io
import logging
import os
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from transformers import pipeline

from src.application.voice.constants import SAMPLE_RATE, TTS_SAMPLE_RATE
from src.infrastructure.implementation.speech import constants

logger = logging.getLogger(__name__)


class SpeechModels:

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.asr = None
        self.tts = None

    @property
    def ready(self) -> bool:
        return self.asr is not None and self.tts is not None

    def load(self) -> None:
        torch.set_num_threads(constants.CPU_THREADS)
        self._load_asr()
        self._load_tts()
        logger.info(constants.MODELS_READY_LOG)

    def _load_asr(self) -> None:
        device = os.getenv(
            constants.ASR_DEVICE_ENV, constants.DEFAULT_ASR_DEVICE
        )
        logger.info(constants.ASR_LOADING_LOG, device)
        self.asr = pipeline(
            constants.ASR_TASK,
            model=constants.ASR_MODEL,
            device=device,
            dtype=torch.float16 if "cuda" in device else torch.float32,
        )

    @staticmethod
    def _tts_path() -> Path:
        cached = Path(torch.hub.get_dir()) / constants.TTS_HUB_PATH
        root = Path(__file__).resolve().parents[4]
        default = cached if cached.exists() else root / constants.TTS_LOCAL_PATH
        return Path(os.getenv(constants.TTS_PATH_ENV, str(default)))

    def _load_tts(self) -> None:
        model_path = self._tts_path()
        if not model_path.exists():
            model_path.parent.mkdir(parents=True, exist_ok=True)
            torch.hub.download_url_to_file(constants.TTS_URL, str(model_path))
        importer = torch.package.PackageImporter(str(model_path))
        self.tts = importer.load_pickle(
            constants.TTS_PACKAGE,
            constants.TTS_OBJECT,
        )
        self.tts.to("cpu")

    def transcribe(self, samples: np.ndarray) -> str:
        result = self.asr(
            {"raw": samples, "sampling_rate": SAMPLE_RATE},
            generate_kwargs={"max_new_tokens": constants.ASR_TOKEN_LIMIT},
        )
        return result["text"].strip()

    def synthesize(self, text: str) -> bytes:
        with torch.inference_mode():
            audio = (
                self.tts.apply_tts(
                    text=text,
                    speaker=constants.TTS_SPEAKER,
                    sample_rate=TTS_SAMPLE_RATE,
                )
                .detach()
                .cpu()
                .numpy()
            )
        output = io.BytesIO()
        sf.write(
            output,
            audio,
            TTS_SAMPLE_RATE,
            format="WAV",
            subtype="PCM_16",
        )
        return output.getvalue()
