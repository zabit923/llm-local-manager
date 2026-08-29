"""
Path-aware CORS (F3.b): разные allow-list per path prefix.

Контекст:
    staff и portal живут на разных origin (admin.payolin.com vs
    portal.payolin.com). Single Starlette CORSMiddleware с объединённым
    списком разрешил бы admin-фронту делать preflight на portal-эндпоинт
    и наоборот.

Реализация:
    Обёртка над Starlette CORSMiddleware — для каждого prefix'а создаём
    отдельный CORSMiddleware-инстанс, поверх одного и того же downstream
    app. На каждом запросе диспетчеризуем по url.path startswith.

    Запросы вне зарегистрированных prefix'ов (/api/v1/wh/, /api/v1/pub/,
    /api/v1/setup/, /docs, /redoc) идут к downstream без CORS — там либо
    server-to-server (webhook/HMAC), либо локальный swagger. Browser
    cross-origin не задуман.

ASGI-уровень (не BaseHTTPMiddleware) — потому что Starlette CORSMiddleware
сам ASGI native и требует доступа к scope/receive/send напрямую.
"""

from dataclasses import dataclass

from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send


@dataclass(frozen=True)
class CorsRouteConfig:
    """
    Конфиг CORS для одного path-prefix. allow_credentials хардкодим True:
    portal/staff оба cookie-based, без credentials CORS бесполезен.
    """

    origins: tuple[str, ...]
    allow_methods: tuple[str, ...]
    allow_headers: tuple[str, ...]


class PathAwareCorsMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        protected_routes: tuple[tuple[str, CorsRouteConfig], ...],
    ) -> None:
        # Каждый prefix получает свой CORSMiddleware-инстанс, все
        # оборачивают один и тот же downstream. Stateless, не interfere.
        self._dispatch: list[tuple[str, ASGIApp]] = [
            (
                prefix,
                CORSMiddleware(
                    app=app,
                    allow_origins=list(cfg.origins),
                    allow_credentials=True,
                    allow_methods=list(cfg.allow_methods),
                    allow_headers=list(cfg.allow_headers),
                ),
            )
            for prefix, cfg in protected_routes
        ]
        self._app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path: str = scope["path"]
        for prefix, cors_app in self._dispatch:
            if path.startswith(prefix):
                await cors_app(scope, receive, send)
                return

        # Путь вне всех охраняемых prefix'ов — без CORS.
        await self._app(scope, receive, send)
