from collections import deque
from collections.abc import Callable, Iterator

import numpy as np

from src.application.voice import constants
from src.application.voice.dto import SpeechEvent
from src.application.voice.errors import InvalidVoicePacket


class UtteranceBuffer:

    def __init__(
        self,
        detector: Callable[[np.ndarray], dict | None],
    ) -> None:
        self._detector = detector
        self._pending = np.empty(0, dtype=np.float32)
        self._preroll = deque(maxlen=constants.PREROLL_FRAMES)
        self._utterance = []
        self._recording = False

    def reset(self) -> None:
        self._pending = np.empty(0, dtype=np.float32)
        self._preroll.clear()
        self._utterance.clear()
        self._recording = False

    def feed(self, raw: bytes) -> Iterator[SpeechEvent]:
        if len(raw) % 2 or len(raw) > constants.MAX_PACKET_BYTES:
            raise InvalidVoicePacket(constants.INVALID_PCM_MESSAGE)
        samples = (
            np.frombuffer(raw, dtype=constants.PCM_DTYPE).astype(
                np.float32,
            )
            / constants.PCM_SCALE
        )
        self._pending = np.concatenate((self._pending, samples))
        while len(self._pending) >= constants.FRAME_SAMPLES:
            frame = self._pending[: constants.FRAME_SAMPLES]
            self._pending = self._pending[constants.FRAME_SAMPLES :]
            event = self._detector(frame)
            if event and "start" in event and not self._recording:
                self._recording = True
                self._utterance = list(self._preroll)
                yield SpeechEvent("start")
            if self._recording:
                self._utterance.append(frame.copy())
            self._preroll.append(frame.copy())
            ended = bool(event and "end" in event)
            limit = len(self._utterance) >= constants.MAX_UTTERANCE_FRAMES
            if self._recording and (ended or limit):
                audio = np.concatenate(self._utterance)
                self.reset()
                yield SpeechEvent(
                    "end",
                    audio,
                    "silence" if ended else "length_limit",
                )
                return
