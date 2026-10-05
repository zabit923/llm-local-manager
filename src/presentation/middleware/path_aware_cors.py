from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from src.presentation.middleware.cors_config import CorsRouteConfig


class PathAwareCorsMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        protected_routes: tuple[tuple[str, CorsRouteConfig], ...],
    ) -> None:
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
        await self._app(scope, receive, send)
