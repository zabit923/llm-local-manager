from abc import abstractmethod

from dataclasses import dataclass


@dataclass(eq=False)
class ApplicationError(Exception):
    @property
    @abstractmethod
    def message(self) -> str: ...
