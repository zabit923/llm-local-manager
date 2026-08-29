from dataclasses import dataclass

from src.domain.ports.error.base import ApplicationError


@dataclass(eq=False)
class InfrastructureError(ApplicationError):
    """
    Маркер инфраструктурных ошибок.

    Семантически отличается от GeneralCustomError: это не вина клиента и
    не нарушение бизнес-правила, а недоступность нашей собственной
    инфраструктуры (БД, кэш, внешний сервис).

    Глобальный exception handler ловит любого потомка и отдаёт 503.
    Не использовать для пробрасывания деталей клиенту — текст уходит только
    в логи.
    """

    text: str = ""
    error: str | None = None

    @property
    def message(self) -> str:
        return self.text or self.__class__.__name__
