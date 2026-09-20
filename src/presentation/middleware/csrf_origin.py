"""
CSRF defence: Origin/Referer check для нескольких prefix'ов с раздельными
allow-list'ами (F1: staff, F2.3: portal).

Контекст:
    SameSite=Strict + CSRF-token double-submit (для portal) — primary
    защита. Этот middleware — defence-in-depth: ловит CSRF-векторы,
    обходящие SameSite (старые браузеры, прокси-настройки, baddly
    configured edge).

    Срабатывает только на mutating-запросы (POST/PUT/PATCH/DELETE) под
    зарегистрированными prefix'ами. GET/HEAD/OPTIONS пропускаются
    (read-only + preflight). Webhook (/api/v1/wh/), public (/api/v1/pub/),
    setup (/api/v1/setup/) не входят ни в один защищаемый prefix —
    не задеваются.

Multi-prefix:
    protected_routes — tuple ((path_prefix, allowed_origins), ...).
    На каждый mutating запрос находится первый prefix match и
    Origin/Referer сверяется ИМЕННО с его allow-list'ом.

    Это важно: staff и portal живут на разных поддоменах
    (admin.payolin.com vs portal.payolin.com). Объединять allow-list'ы
    в один frozenset нельзя — это разрешит staff-фронту слать запросы
    на portal-эндпоинты и наоборот.

    Запросы на путь вне всех зарегистрированных prefix'ов пропускаются
    без проверки (webhook/public/setup).
"""

from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Mutating HTTP-методы. Только они проверяются — GET/HEAD/OPTIONS
# не могут вызвать побочный эффект в корректно спроектированном API.
_MUTATING_METHODS: frozenset[str] = frozenset(
    {"POST", "PUT", "PATCH", "DELETE"}
)


class OriginCheckMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        protected_routes: tuple[tuple[str, frozenset[str]], ...],
    ) -> None:
        super().__init__(app=app)
        # Pre-compute referer-prefixes для каждого route. Каждый элемент:
        # (path_prefix, allowed_origins, referer_prefix_tuple).
        # Pre-compute чтобы на горячем пути не было work'а на каждый запрос.
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
        if request.method not in _MUTATING_METHODS:
            return await call_next(request)

        # Найти первый prefix match. Если нет — путь не охраняется
        # (webhook/public/setup), пропускаем.
        match: tuple[frozenset[str], tuple[str, ...]] | None = None
        for prefix, allowed, referer_prefixes in self._routes:
            if request.url.path.startswith(prefix):
                match = (allowed, referer_prefixes)
                break
        if match is None:
            return await call_next(request)

        allowed, referer_prefixes = match

        origin = request.headers.get("origin")
        if origin is not None:
            if origin not in allowed:
                return JSONResponse(
                    status_code=403,
                    content={"error": "csrf_origin_check_failed"},
                )
            return await call_next(request)

        referer = request.headers.get("referer")
        if referer is not None:
            if any(referer.startswith(p) for p in referer_prefixes):
                return await call_next(request)
            return JSONResponse(
                status_code=403,
                content={"error": "csrf_referer_check_failed"},
            )

        return JSONResponse(
            status_code=403,
            content={"error": "csrf_missing_origin"},
        )
