from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Mutating HTTP-методы. Только они проверяются — GET/HEAD/OPTIONS
# не могут вызвать побочный эффект в корректно спроектированном API.
from src.presentation import constants


class OriginCheckMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        protected_routes: tuple[tuple[str, frozenset[str]], ...],
    ) -> None:
        super().__init__(app=app)
        self._routes: tuple[
            tuple[str, frozenset[str], tuple[str, ...]], ...
        ] = tuple(
            (
                path_prefix,
                allowed,
                tuple(f"{o}/" for o in allowed),
            )
            for path_prefix, allowed in protected_routes
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method not in constants.MUTATING_METHODS:
            return await call_next(request)
        match = next(
            (
                (allowed, referer_prefixes)
                for prefix, allowed, referer_prefixes in self._routes
                if request.url.path.startswith(prefix)
            ),
            None,
        )
        if match is None:
            return await call_next(request)
        error = self._origin_error(request, *match)
        if error:
            return JSONResponse(status_code=403, content={"error": error})
        return await call_next(request)

    @staticmethod
    def _origin_error(
        request: Request,
        allowed: frozenset[str],
        prefixes: tuple[str, ...],
    ) -> str | None:
        origin = request.headers.get("origin")
        if origin is not None:
            return None if origin in allowed else constants.CSRF_ORIGIN_ERROR
        referer = request.headers.get("referer")
        if referer is not None:
            return (
                None
                if any(referer.startswith(prefix) for prefix in prefixes)
                else constants.CSRF_REFERER_ERROR
            )
        return constants.CSRF_MISSING_ORIGIN_ERROR
