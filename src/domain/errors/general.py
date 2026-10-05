from dataclasses import dataclass

from src.domain.constants import GENERAL_ERROR_MESSAGE
from src.domain.ports.error.base import ApplicationError
from src.domain.types.model_id import ModelIdType
from src.domain.types.model_id_uuid import ModelIdUuidType


@dataclass(eq=False)
class GeneralCustomError(ApplicationError):
    text: str
    model_name: str | None = None
    error: str | None = None
    model_id: ModelIdType | ModelIdUuidType | None = None
    log_warn: str | None = None
    # Optional. Если задано — application_error_handler добавит
    # Retry-After в HTTP-ответ. Используется для 423/429
    # (lockout, rate-limit). Семантика: число секунд до момента,
    # когда клиенту имеет смысл повторить запрос.
    retry_after_sec: int | None = None

    @property
    def message(self):
        return GENERAL_ERROR_MESSAGE.format(
            model=self.model_name,
            id=self.model_id,
            text=self.text,
            error=self.error,
        )

    def __str__(self):
        return self.message
