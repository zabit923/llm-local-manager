import os

from src.domain.configs.app_env import AppEnv
from src.entrypoint.config.loader import (
    build_db_url,
    build_db_test_url,
    build_redis_url,
    read_secret_or_env,
)
from src.entrypoint.config.settings import (
    DbSettings,
    EncryptionSettings,
    JWTSettings,
    RedisCacheSettings,
    Settings,
    WorkerSettings,
)


class SettingsBuilder:
    def __init__(
        self,
    ) -> None:
        self._dummy_key: bytes = b"\x00" * 32

    def _read_encryption_key(
        self,
        secret_name: str,
        env_var: str,
    ) -> bytes:
        raw = read_secret_or_env(secret_name, env_var, "").encode()
        if len(raw) == 64:
            return bytes.fromhex(raw.decode())
        if len(raw) == 32:
            return raw
        raise ValueError(
            f"Encryption key '{secret_name}' must be 32 raw bytes or 64 hex chars, "
            f"got {len(raw)} bytes"
        )

    def _make_encryption(
        self,
        app_env: AppEnv,
    ) -> EncryptionSettings:
        if app_env == AppEnv.local:
            return EncryptionSettings(
                signing_secret_key=self._dummy_key,
                invoice_field_key=self._dummy_key,
                webhook_secret_key=self._dummy_key,
                portal_csrf_secret=self._dummy_key,
            )
        return EncryptionSettings(
            signing_secret_key=self._read_encryption_key(
                secret_name="signing_secret_key",
                env_var="SIGNING_SECRET_ENC_KEY",
            ),
            invoice_field_key=self._read_encryption_key(
                secret_name="invoice_field_encryption_key",
                env_var="INVOICE_FIELD_ENC_KEY",
            ),
            webhook_secret_key=self._read_encryption_key(
                secret_name="webhook_secret_key",
                env_var="WEBHOOK_SECRET_ENC_KEY",
            ),
            portal_csrf_secret=self._read_encryption_key(
                secret_name="portal_csrf_secret",
                env_var="PORTAL_CSRF_SECRET",
            ),
        )

    def _make_jwt(
        self,
        app_env: AppEnv,
    ) -> JWTSettings:
        if app_env == AppEnv.local:
            return JWTSettings(secret_key=self._dummy_key)
        return JWTSettings(
            secret_key=self._read_encryption_key(
                secret_name="jwt_secret_key",
                env_var="JWT_SECRET_KEY",
            ),
        )

    def _get_app_env(self) -> AppEnv:
        raw_env = os.environ.get("FASTAPI_CFG__APP_ENV")
        if raw_env is None:
            raise RuntimeError(
                "FASTAPI_CFG__APP_ENV is not set. "
                "Must be one of: " + ", ".join(e.value for e in AppEnv)
            )
        try:
            return AppEnv(raw_env)
        except ValueError:
            raise RuntimeError(
                f"FASTAPI_CFG__APP_ENV={raw_env!r} is invalid. "
                "Must be one of: " + ", ".join(e.value for e in AppEnv)
            )

    # def _make_portal_auth(
    #     self,
    #     app_env: AppEnv,
    # ) -> PortalAuthConfig:
    #     """
    #     PortalAuthConfig с env-зависимыми cookie-полями.
    #
    #     local:
    #       - cookies без __Host- префикса (на http://localhost браузер
    #         __Host- + Secure не примет — Secure требует HTTPS).
    #       - cookie_secure_default=False.
    #     test/prod:
    #       - cookies с __Host- префиксом (host-only, Path=/, Secure).
    #       - cookie_secure_default=True.
    #
    #     Остальные поля (TTL, lockout schedule, CSRF len и т.д.) — дефолты
    #     PortalAuthConfig dataclass. Тюнинг — правка default в dataclass'е
    #     либо расширение этого метода с чтением из env.
    #     """
    #     is_local = app_env == AppEnv.local
    #     return PortalAuthConfig(
    #         cookie_session_name=(
    #             "payolin_portal_session" if is_local else "__Host-portal_session"
    #         ),
    #         cookie_csrf_name=(
    #             "payolin_portal_csrf" if is_local else "__Host-portal_csrf"
    #         ),
    #         cookie_secure_default=not is_local,
    #     )

    def execute(
        self,
    ) -> Settings:
        app_env = self._get_app_env()
        broker_url = build_redis_url(db=0)
        jwt_settings = self._make_jwt(app_env=app_env)
        return Settings(
            app_env=app_env,
            db=DbSettings(
                url=build_db_url(app_env=app_env),
                test_url=build_db_test_url(),
            ),
            worker=WorkerSettings(
                broker_url=broker_url,
                result_backend=broker_url,
            ),
            jwt=jwt_settings,
            redis_cache=RedisCacheSettings(
                url=build_redis_url(db=1),
            ),
            encryption=self._make_encryption(app_env=app_env),
        )


settings_builder = SettingsBuilder()
settings = settings_builder.execute()
