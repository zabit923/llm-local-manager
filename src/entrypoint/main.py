import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from dishka.integrations import fastapi as fastapi_integration

from src.presentation.exception_handlers import register_exception_handlers
from src.presentation.middleware.csrf_origin import OriginCheckMiddleware
from src.domain.configs.app_env import AppEnv
from src.presentation.middleware.path_aware_cors import (
    CorsRouteConfig,
    PathAwareCorsMiddleware,
)
from src.presentation.middleware.security_headers import SecurityHeadersMiddleware
from src.presentation.routers.http import router as http_router
from src.entrypoint.logging.setup import setup_logging
from src.entrypoint.config.setup_db import app_db
from src.entrypoint.ioc import setup_di
from src.entrypoint.config.build import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

    # Shutdown
    await app.state.dishka_container.close()
    await app_db.dispose()


def create_app() -> FastAPI:
    container = setup_di()
    setup_logging(app_env=settings.app_env)

    is_prod = settings.app_env == AppEnv.prod

    app = FastAPI(
        root_path=settings.names.path,
        title=settings.names.title,
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
    )

    # Порядок add_middleware: Starlette оборачивает последний добавленный
    # САМЫМ ВНЕШНИМ. Желаемый chain снаружи внутрь:
    #   SecurityHeaders → PathAwareCors → OriginCheck → app
    # Это значит SecurityHeaders видит ВСЕ ответы (включая 403 от
    # OriginCheck и CORS preflight). CORS обрабатывает preflight ДО
    # OriginCheck (тот пропускает OPTIONS как safe method).
    # Порядок в коде — обратный (от внутреннего к внешнему):
    app.add_middleware(
        OriginCheckMiddleware,
        protected_routes=(
            ("/api/v1/staff/", frozenset(settings.middleware.admin_origins)),
            ("/api/v1/portal/", frozenset(settings.middleware.portal_origins)),
        ),
    )

    _allow_methods = tuple(settings.middleware.allow_methods)
    _allow_headers = tuple(settings.middleware.allow_headers)
    app.add_middleware(
        PathAwareCorsMiddleware,
        protected_routes=(
            (
                "/api/v1/staff/",
                CorsRouteConfig(
                    origins=tuple(settings.middleware.admin_cors_origins),
                    allow_methods=_allow_methods,
                    allow_headers=_allow_headers,
                ),
            ),
            (
                "/api/v1/portal/",
                CorsRouteConfig(
                    origins=tuple(settings.middleware.portal_cors_origins),
                    allow_methods=_allow_methods,
                    allow_headers=_allow_headers,
                ),
            ),
        ),
    )
    app.add_middleware(middleware_class=SecurityHeadersMiddleware)

    app.include_router(router=http_router)
    register_exception_handlers(app=app)
    fastapi_integration.setup_dishka(container=container, app=app)

    return app
