import numpy as np
import torch


class SileroDetector:

    def __init__(self, iterator) -> None:
        self._iterator = iterator

    def __call__(self, samples: np.ndarray) -> dict | None:
        return self._iterator(torch.from_numpy(samples))

    def reset_states(self) -> None:
        self._iterator.reset_states()
