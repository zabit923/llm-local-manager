import logging

from aiohttp import ClientError as AiohttpClientError
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from redis.exceptions import RedisError
from sqlalchemy.exc import DBAPIError, OperationalError

from src.domain.errors.general import GeneralCustomError
from src.domain.ports.error.base import ApplicationError
from src.domain.ports.error.infrastructure import InfrastructureError
from src.presentation.exception_handlers.mapping import resolve

logger = logging.getLogger(__name__)


# Единое значение Retry-After для всех 503. Клиент должен повторить запрос
# через это число секунд. 30 сек — окно достаточное чтобы worker успел
# отработать reconcile registry или чтобы Redis/Postgres подняться после
# кратковременного сбоя.
RETRY_AFTER_SECONDS = "30"


def _request_context(
    request: Request,
) -> str:
    """Короткий префикс для лога — без PII, без body, только path и method."""
    return f"{request.method} {request.url.path}"


async def application_error_handler(
    request: Request,
    exc: ApplicationError,
) -> ORJSONResponse:
    """
    Бизнес-ошибки и ошибки валидации доменного уровня.
    Лог уровня INFO без traceback — это ожидаемая ветка.

    Если конкретный класс не смаппен — попадаем в дефолт (400 application_error)
    и пишем WARNING: значит ошибку добавили, в карту записать забыли.
    """
    http_status, error_code = resolve(error=exc)

    if error_code == "application_error":
        logger.warning(
            "unmapped application error: type=%s %s cause=%s",
            type(exc).__name__,
            _request_context(request=request),
            str(exc)[:256],
        )
    else:
        logger.info(
            "%s %s cause=%s",
            error_code,
            _request_context(request=request),
            str(exc)[:256],
        )

    headers: dict[str, str] | None = None
    if isinstance(exc, GeneralCustomError) and exc.retry_after_sec is not None:
        # Retry-After: число секунд (RFC 7231). Min=1 чтобы клиент не
        # ретраил мгновенно при граничном remaining=0.
        headers = {"Retry-After": str(max(exc.retry_after_sec, 1))}

    return ORJSONResponse(
        status_code=http_status,
        content={"error": error_code},
        headers=headers,
    )


async def infrastructure_error_handler(
    request: Request,
    exc: InfrastructureError,
) -> ORJSONResponse:
    """
    Доменно-маркированные инфраструктурные ошибки (наши явные подклассы).
    Всегда 503. Лог WARNING с коротким cause — без traceback.
    """
    error_code = exc.error or "service_unavailable"
    logger.warning(
        "infrastructure error: type=%s %s cause=%s",
        type(exc).__name__,
        _request_context(request=request),
        exc.message,
    )
    return ORJSONResponse(
        status_code=503,
        content={"error": error_code},
        headers={"Retry-After": RETRY_AFTER_SECONDS},
    )


async def aiohttp_error_handler(
    request: Request,
    exc: AiohttpClientError,
) -> ORJSONResponse:
    """
    Внешний сервис (банк) сетево/HTTP недоступен.
    Сюда попадают timeout, connection refused, DNS — всё что aiohttp кидает
    своим иерархическим исключением.
    """
    logger.warning(
        "external service unavailable: type=%s %s cause=%s",
        type(exc).__name__,
        _request_context(request=request),
        str(exc)[:256],
    )
    return ORJSONResponse(
        status_code=503,
        content={"error": "external_service_unavailable"},
        headers={"Retry-After": RETRY_AFTER_SECONDS},
    )


async def redis_error_handler(
    request: Request,
    exc: RedisError,
) -> ORJSONResponse:
    logger.warning(
        "cache unavailable: type=%s %s cause=%s",
        type(exc).__name__,
        _request_context(request=request),
        str(exc)[:256],
    )
    return ORJSONResponse(
        status_code=503,
        content={"error": "cache_unavailable"},
        headers={"Retry-After": RETRY_AFTER_SECONDS},
    )


async def database_error_handler(
    request: Request,
    exc: DBAPIError,
) -> ORJSONResponse:
    """
    Соединение с Postgres/драйвером сломано.
    OperationalError — DBAPIError, FastAPI сматчит этот handler по MRO.
    Прикладные IntegrityError здесь НЕ ловим — они уже обёрнуты в
    GeneralCustomError на уровне gateway'ев пойдут в application_error_handler.
    """
    if not isinstance(exc, OperationalError):
        # Не наш случай — пробрасываем дальше в fallback 500.
        raise exc

    logger.error(
        "database unavailable: type=%s %s cause=%s",
        type(exc).__name__,
        _request_context(request=request),
        str(exc)[:256],
    )
    return ORJSONResponse(
        status_code=503,
        content={"error": "database_unavailable"},
        headers={"Retry-After": RETRY_AFTER_SECONDS},
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> ORJSONResponse:
    """
    Pydantic-валидация запроса. Унифицируем под наш формат.
    Поля сжимаем до loc + msg + type — без значений (могут быть PII).
    """
    fields = [
        {
            "loc": list(err.get("loc", [])),
            "msg": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in exc.errors()
    ]
    logger.info(
        "validation_error %s fields=%d first=%s",
        _request_context(request=request),
        len(fields),
        f"{fields[0]['loc']}:{fields[0]['type']}" if fields else "-",
    )
    return ORJSONResponse(
        status_code=422,
        content={"error": "validation_error", "fields": fields},
    )


async def unhandled_error_handler(
    request: Request,
    exc: Exception,
) -> ORJSONResponse:
    """
    Последняя стенка. Любое исключение, не пойманное специфичными handler'ами,
    приземляется сюда. Это ЕДИНСТВЕННОЕ место где пишем traceback.
    """
    logger.critical(
        "unhandled exception: %s",
        _request_context(request=request),
        exc_info=exc,
    )
    return ORJSONResponse(
        status_code=500,
        content={"error": "internal_error"},
    )
