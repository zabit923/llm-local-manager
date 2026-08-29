from aiohttp import ClientError as AiohttpClientError
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from redis.exceptions import RedisError
from sqlalchemy.exc import DBAPIError

from src.domain.ports.error.base import ApplicationError
from src.domain.ports.error.infrastructure import InfrastructureError
from src.presentation.exception_handlers.handlers import (
    aiohttp_error_handler,
    application_error_handler,
    database_error_handler,
    infrastructure_error_handler,
    redis_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)

def register_exception_handlers(app: FastAPI) -> None:
    """
    Регистрация глобальных обработчиков исключений.

    Порядок регистрации важен только для перекрывающихся типов: FastAPI выбирает
    самый специфичный из зарегистрированных по MRO. Поскольку InfrastructureError
    наследник ApplicationError — handler для InfrastructureError должен быть
    зарегистрирован, иначе все его потомки уйдут в application_error_handler.

    Catch-all на Exception ловит ВСЁ что не было поймано выше.

    type: ignore[arg-type] — Starlette типизирует handler как
    Callable[[Request, Exception], ...]. Сужение второго параметра до
    конкретного подкласса безопасно (FastAPI диспатчит по типу), но
    pyright/mypy формально ругаются на ковариантность.
    """
    # Прикладные ошибки
    app.add_exception_handler(ApplicationError, application_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(InfrastructureError, infrastructure_error_handler)  # type: ignore[arg-type]

    # Pydantic валидация
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]

    # Native infrastructure
    app.add_exception_handler(AiohttpClientError, aiohttp_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RedisError, redis_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(DBAPIError, database_error_handler)  # type: ignore[arg-type]

    # Catch-all
    app.add_exception_handler(Exception, unhandled_error_handler) # type: ignore[arg-type]
