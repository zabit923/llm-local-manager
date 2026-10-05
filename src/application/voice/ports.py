import asyncio
from typing import Protocol

import numpy as np


class SpeechInference(Protocol):

    lock: asyncio.Lock

    def transcribe(self, samples: np.ndarray) -> str: ...

    def synthesize(self, text: str) -> bytes: ...


class OrderingAgent(Protocol):

    async def message(self, session_id: str, text: str) -> dict: ...


class SpeechDetector(Protocol):

    def __call__(self, samples: np.ndarray) -> dict | None: ...

    def reset_states(self) -> None: ...
