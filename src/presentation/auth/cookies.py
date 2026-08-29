"""
Cookie helpers для admin auth (F1).

Зачем helper, а не inline в view:
    атрибуты cookie централизованы. Изменить TTL / Path / SameSite —
    одно место. Случайно забыть Secure в prod — невозможно.

Контракт:
    - set_auth_cookies / clear_auth_cookies оперируют Response из view'а
    - read_* — извлекают raw-токены из Request, без декодирования
      (декодирование — задача JWTService)
    - все cookie attrs (TTL, Path, Secure, SameSite) берутся из
      AdminAuthConfig. TTL в config синхронизированы с JWT exp через
      build.py — никаких рассинхронов.
"""

from fastapi import Request, Response


# def set_auth_cookies(
#     response: Response,
#     access_token: str,
#     refresh_token: str,
#     auth_config: AdminAuthConfig,
# ) -> None:
#     """Поставить access + refresh cookies на ответ."""
#     response.set_cookie(
#         key=auth_config.cookie_access_name,
#         value=access_token,
#         max_age=auth_config.access_ttl_sec,
#         path=auth_config.cookie_access_path,
#         secure=auth_config.cookie_secure_default,
#         httponly=True,
#         samesite=auth_config.cookie_samesite,
#     )
#     response.set_cookie(
#         key=auth_config.cookie_refresh_name,
#         value=refresh_token,
#         max_age=auth_config.refresh_ttl_sec,
#         path=auth_config.cookie_refresh_path,
#         secure=auth_config.cookie_secure_default,
#         httponly=True,
#         samesite=auth_config.cookie_samesite,
#     )
#
#
# def clear_auth_cookies(
#     response: Response,
#     auth_config: AdminAuthConfig,
# ) -> None:
#     """
#     Удалить cookies в браузере.
#
#     Браузер удалит cookie ТОЛЬКО если Path/SameSite/Secure совпадают
#     с теми, с которыми cookie был установлен. Поэтому delete_cookie
#     передаём те же атрибуты что в set_auth_cookies.
#     """
#     response.delete_cookie(
#         key=auth_config.cookie_access_name,
#         path=auth_config.cookie_access_path,
#         secure=auth_config.cookie_secure_default,
#         httponly=True,
#         samesite=auth_config.cookie_samesite,
#     )
#     response.delete_cookie(
#         key=auth_config.cookie_refresh_name,
#         path=auth_config.cookie_refresh_path,
#         secure=auth_config.cookie_secure_default,
#         httponly=True,
#         samesite=auth_config.cookie_samesite,
#     )
#
#
# def read_access_token(
#     request: Request,
#     auth_config: AdminAuthConfig,
# ) -> str | None:
#     """
#     Извлечь raw access token из cookie. None если cookie отсутствует.
#
#     Декодирование/валидация — задача JWTService на стороне dependency,
#     здесь только транспортный уровень.
#     """
#     return request.cookies.get(auth_config.cookie_access_name)
#
#
# def read_refresh_token(
#     request: Request,
#     auth_config: AdminAuthConfig,
# ) -> str | None:
#     """Извлечь raw refresh token из cookie. None если отсутствует."""
#     return request.cookies.get(auth_config.cookie_refresh_name)
