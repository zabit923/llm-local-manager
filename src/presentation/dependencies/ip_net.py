"""
Извлечение client IP / User-Agent из FastAPI Request.

Используется при сборке actor-DTO (AdminActor / MerchantActor) для audit_log
и при IP/UA binding-проверке portal-сессий (F2.3+).

Trust X-Forwarded-For:
    Допустим только потому что весь HTTP-трафик идёт через наш собственный
    edge nginx, который перезаписывает XFF chain. Первый элемент XFF —
    реальный IP клиента (nginx prepend'ит).

    Для public/webhook эндпоинтов (где edge доверять нельзя — клиент может
    спуфить XFF до того как добраться до nginx) этот helper использовать
    НЕЛЬЗЯ. Там доверяется только request.client.host.

Ограничения длины:
    Согласованы с моделью AuditLog (String(45) для ip_address, String(512)
    для user_agent). Обрезаем на входе чтобы гарантированно не падать на
    INSERT даже если кто-то пришлёт огромный заголовок.
"""

from fastapi import Request

from src.domain.constants import IP_MAX_LEN, USER_AGENT_MAX_LEN


def extract_client_ip(
    request: Request,
) -> str | None:
    """
    Реальный IP клиента с учётом edge-архитектуры:
        client → nginx@edge → traefik → FastAPI

    nginx@edge формирует X-Forwarded-For добавлением real client IP
    к existing chain. Берём первый элемент.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",", 1)[0].strip()
        if first:
            return first[:IP_MAX_LEN]
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()[:IP_MAX_LEN]
    return request.client.host[:IP_MAX_LEN] if request.client else None


def extract_user_agent(
    request: Request,
) -> str | None:
    user_agent = request.headers.get("user-agent")
    return user_agent[:USER_AGENT_MAX_LEN] if user_agent else None
