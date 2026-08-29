import pytz
from typing import ClassVar, Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.domain.configs.app_env import AppEnv
from src.domain.constants import (
    NAMING_CONVENTION,
    NONCE_SIZE,
    TIMEZONE,
    VERSION_PREFIX,
)


class RunConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8888


class ProjectName(BaseModel):
    title: str = "Payolin"
    path: str = ""  # TODO
    access: str = "Access to Payolin."


class DbSettings(BaseModel):
    url: str
    test_url: str
    echo: bool = False
    echo_pool: bool = False
    max_overflow: int = 5
    pool_size: int = 3
    pool_timeout: int = 10
    pool_recycle: int = 1800
    pool_pre_ping: bool = True
    naming_convention: dict[str, str] = NAMING_CONVENTION

    @property
    def asyncpg_url(self) -> str:
        return self.url.replace("postgresql+asyncpg://", "postgresql://")


class WorkerSettings(BaseModel):
    broker_url: str
    result_backend: str
    result_ex_time: int = 1000


class RedisCacheSettings(BaseModel):
    """
    Redis DB 1 — balance_cache + merchant_auth_cache.
    Изолирован от TaskIQ (DB 0).
    При переходе на Sentinel: sentinel_hosts + sentinel_master_name,
    менять только provide_cache_redis в ioc.py.
    """

    url: str
    sentinel_master_name: str = "my_master_redis"
    sentinel_hosts: list[tuple[str, int]] = []


class EncryptionSettings(BaseModel):
    nonce_size: ClassVar[int] = NONCE_SIZE
    version_prefix: ClassVar[Literal[b"v1:"]] = VERSION_PREFIX
    signing_secret_key: bytes
    invoice_field_key: bytes
    webhook_secret_key: bytes
    # CSRF HMAC secret — отдельный slot, не пересекается с другими
    # encryption ключами (defense in depth: утечка одного не компрометирует
    # другое). 32 raw bytes / 64 hex.
    portal_csrf_secret: bytes


class MiddlewareSettings(BaseModel):
    # --- CORS allow-lists per-prefix (F3.b) ---
    # admin + portal — два разных фронта на разных origin. Объединять
    # списки нельзя: admin-фронт получил бы CORS-разрешение на portal-
    # эндпоинт. Defence in depth поверх OriginCheckMiddleware (тот
    # охраняет только mutating; CORS preflight охватывает все методы).
    # allow_credentials=True у обоих — никаких "*" в origins.
    admin_cors_origins: list[str] = ["http://localhost:5173"]
    portal_cors_origins: list[str] = ["http://localhost:5174"]
    # X-CSRF-Token обязателен для portal mutating запросов
    # (double-submit pattern, см. CsrfService). Без него preflight
    # на /api/v1/portal/* mutating endpoints отвергнется браузером.
    allow_methods: list[str] = ["GET", "POST", "PATCH", "OPTIONS", "DELETE"]
    allow_headers: list[str] = ["Authorization", "Content-Type", "X-CSRF-Token"]

    # --- CSRF Origin allow-list (F1) ---
    # Allow-list для Origin/Referer проверки на mutating запросы под
    # /api/v1/staff/. Отдельно от cors_origins: cors_origins — про CORS
    # preflight, admin_origins — про CSRF defence-in-depth (SameSite=Strict
    # уже отрезает основной вектор, это второй слой).
    # Точное равенство. Без wildcard. В prod — только https://binrt.ru.
    admin_origins: list[str] = ["http://localhost:5173"]
    portal_origins: list[str] = ["http://localhost:5174"]


class ApiV1Prefix(BaseModel):
    prefix: str = "/v1"
    auth: str = "/auth"
    pub: str = "/pub"
    admin: str = "/admin"


class ApiPrefix(BaseModel):
    prefix: str = "/api"
    v1: ApiV1Prefix = ApiV1Prefix()

    @property
    def bearer_token_url(self) -> str:
        parts = (self.prefix, self.v1.prefix, self.v1.auth, "/login")
        return "".join(parts).removeprefix("/")


class JWTSettings(BaseModel):
    secret_key: bytes
    algorithm: str = "HS256"
    access_expire_minutes: int = 15
    refresh_expire_hours: int = 24
    pre_auth_expire_seconds: int = 300


class BalanceReconcileSettings(BaseModel):
    # 2 сек — короткий FOR UPDATE на merchant в платёжных путях обычно
    # держится миллисекунды; 2с покрывает редкие медленные tx, при этом
    # повисший платёж > 2с пропускается без блокировки reconcile.
    lock_timeout_ms: int = 2000
    # 25 мин — смещение от merchant_auth.registry_reconcile_seconds (1800),
    # чтобы пики CPU/Postgres-локов не стакались.
    reconcile_seconds: int = 1500


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.template", ".env"),
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="FASTAPI_CFG__",
        extra="ignore",
    )
    app_env: AppEnv
    tz: pytz.tzinfo.BaseTzInfo = TIMEZONE
    run: RunConfig = RunConfig()
    db: DbSettings
    worker: WorkerSettings
    redis_cache: RedisCacheSettings
    encryption: EncryptionSettings
    jwt: JWTSettings
    middleware: MiddlewareSettings = MiddlewareSettings()
    names: ProjectName = ProjectName()
    balance_reconcile: BalanceReconcileSettings = BalanceReconcileSettings()
    api: ApiPrefix = ApiPrefix()
