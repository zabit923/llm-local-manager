from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SpeechEvent:

    kind: str
    samples: np.ndarray | None = None
    reason: str | None = None
