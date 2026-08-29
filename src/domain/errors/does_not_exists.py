from dataclasses import dataclass

from src.domain.ports.error.base import ApplicationError
from src.domain.types.model_id import ModelIdType
from src.domain.types.model_id_uuid import ModelIdUuidType


@dataclass(eq=False)
class CustomDoesNotExist(ApplicationError):
    class_name: str
    model_id: ModelIdType | ModelIdUuidType | None = None

    @property
    def message(self):
        text = f"{self.class_name} does not exist with id: {self.model_id}"
        return text
