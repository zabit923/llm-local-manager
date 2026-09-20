import logging
from dataclasses import dataclass

from src.domain.ports.error.base import ApplicationError
from src.domain.types.model_id import ModelIdType
from src.domain.types.model_id_uuid import ModelIdUuidType

logger = logging.getLogger(__name__)


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
        log_text = (
            f":=GCE| Model={self.model_name}, id={self.model_id}, "
            f"text={self.text}, error={self.error}"
        )
        logger.debug(log_text)
        if self.log_warn:
            logger.warning(self.log_warn)
        return log_text

    def __str__(self):
        return self.message
