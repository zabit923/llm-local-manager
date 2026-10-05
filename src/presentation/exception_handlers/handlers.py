import logging

from aiohttp import ClientError as AiohttpClientError
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy.exc import DBAPIError, OperationalError

from src.domain.errors.general import GeneralCustomError
from src.domain.ports.error.base import ApplicationError
from src.domain.ports.error.infrastructure import InfrastructureError
from src.presentation.exception_handlers import constants
from src.presentation.exception_handlers.mapping import resolve

logger = logging.getLogger(__name__)


RETRY_AFTER_SECONDS = constants.RETRY_AFTER_SECONDS


def _request_context(
    request: Request,
) -> str:
    return f"{request.method} {request.url.path}"


async def application_error_handler(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    http_status, error_code = resolve(error=exc)
    if isinstance(exc, GeneralCustomError) and exc.log_warn:
        logger.warning(exc.log_warn)

    if error_code == constants.APPLICATION_ERROR:
        logger.warning(
            constants.UNMAPPED_LOG,
            type(exc).__name__,
            _request_context(request=request),
            str(exc)[:256],
        )
    else:
        logger.info(
            constants.APPLICATION_LOG,
            error_code,
            _request_context(request=request),
            str(exc)[:256],
        )

    headers: dict[str, str] | None = None
    if isinstance(exc, GeneralCustomError) and exc.retry_after_sec is not None:
        headers = {"Retry-After": str(max(exc.retry_after_sec, 1))}

    return JSONResponse(
        status_code=http_status,
        content={"error": error_code},
        headers=headers,
    )


async def infrastructure_error_handler(
    request: Request,
    exc: InfrastructureError,
) -> JSONResponse:
    error_code = exc.error or constants.SERVICE_UNAVAILABLE
    logger.warning(
        constants.INFRASTRUCTURE_LOG,
        type(exc).__name__,
        _request_context(request=request),
        exc.message,
    )
    return JSONResponse(
        status_code=503,
        content={"error": error_code},
        headers={"Retry-After": RETRY_AFTER_SECONDS},
    )


async def aiohttp_error_handler(
    request: Request,
    exc: AiohttpClientError,
) -> JSONResponse:
    logger.warning(
        constants.EXTERNAL_LOG,
        type(exc).__name__,
        _request_context(request=request),
        str(exc)[:256],
    )
    return JSONResponse(
        status_code=503,
        content={"error": constants.EXTERNAL_UNAVAILABLE},
        headers={"Retry-After": RETRY_AFTER_SECONDS},
    )


async def redis_error_handler(
    request: Request,
    exc: RedisError,
) -> JSONResponse:
    logger.warning(
        constants.CACHE_LOG,
        type(exc).__name__,
        _request_context(request=request),
        str(exc)[:256],
    )
    return JSONResponse(
        status_code=503,
        content={"error": constants.CACHE_UNAVAILABLE},
        headers={"Retry-After": RETRY_AFTER_SECONDS},
    )


async def database_error_handler(
    request: Request,
    exc: DBAPIError,
) -> JSONResponse:
    if not isinstance(exc, OperationalError):
        raise exc

    logger.error(
        constants.DATABASE_LOG,
        type(exc).__name__,
        _request_context(request=request),
        str(exc)[:256],
    )
    return JSONResponse(
        status_code=503,
        content={"error": constants.DATABASE_UNAVAILABLE},
        headers={"Retry-After": RETRY_AFTER_SECONDS},
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    fields = [
        {
            "loc": list(err.get("loc", [])),
            "msg": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in exc.errors()
    ]
    logger.info(
        constants.VALIDATION_LOG,
        _request_context(request=request),
        len(fields),
        f"{fields[0]['loc']}:{fields[0]['type']}" if fields else "-",
    )
    return JSONResponse(
        status_code=422,
        content={"error": constants.VALIDATION_ERROR, "fields": fields},
    )


async def unhandled_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.critical(
        constants.UNHANDLED_LOG,
        _request_context(request=request),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"error": constants.INTERNAL_ERROR},
    )
