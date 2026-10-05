import logging
from contextlib import asynccontextmanager

from dishka import AsyncContainer
from dishka.integrations import fastapi as fastapi_integration
from fastapi import FastAPI

from src.domain.configs.app_env import AppEnv
from src.entrypoint.config.build import settings
from src.entrypoint.ioc import setup_di
from src.entrypoint.logging.setup import setup_logging
from src.presentation import constants
from src.presentation.exception_handlers import register_exception_handlers
from src.presentation.middleware.cors_config import CorsRouteConfig
from src.presentation.middleware.csrf_origin import OriginCheckMiddleware
from src.presentation.middleware.path_aware_cors import PathAwareCorsMiddleware
from src.presentation.middleware.security_headers import (
    SecurityHeadersMiddleware,
)
from src.presentation.routers.http import router as http_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await app.state.dishka_container.close()


def create_app(container: AsyncContainer | None = None) -> FastAPI:
    container = setup_di() if container is None else container
    setup_logging(app_env=settings.app_env)

    is_prod = settings.app_env == AppEnv.prod

    app = FastAPI(
        root_path=settings.names.path,
        title=settings.names.title,
        lifespan=lifespan,
        docs_url=None if is_prod else constants.DOCS_PATH,
        redoc_url=None if is_prod else constants.REDOC_PATH,
        openapi_url=None if is_prod else constants.OPENAPI_PATH,
    )

    configure_middleware(app)

    app.include_router(router=http_router)
    register_exception_handlers(app=app)
    fastapi_integration.setup_dishka(container=container, app=app)

    return app


def configure_middleware(app: FastAPI) -> None:
    app.add_middleware(
        OriginCheckMiddleware,
        protected_routes=(
            (
                constants.STAFF_PATH_PREFIX,
                frozenset(settings.middleware.admin_origins),
            ),
            (
                constants.PORTAL_PATH_PREFIX,
                frozenset(settings.middleware.portal_origins),
            ),
        ),
    )

    allow_methods = tuple(settings.middleware.allow_methods)
    allow_headers = tuple(settings.middleware.allow_headers)
    app.add_middleware(
        PathAwareCorsMiddleware,
        protected_routes=(
            (
                constants.STAFF_PATH_PREFIX,
                CorsRouteConfig(
                    origins=tuple(settings.middleware.admin_cors_origins),
                    allow_methods=allow_methods,
                    allow_headers=allow_headers,
                ),
            ),
            (
                constants.PORTAL_PATH_PREFIX,
                CorsRouteConfig(
                    origins=tuple(settings.middleware.portal_cors_origins),
                    allow_methods=allow_methods,
                    allow_headers=allow_headers,
                ),
            ),
        ),
    )
    app.add_middleware(middleware_class=SecurityHeadersMiddleware)
