import os
from pathlib import Path
from urllib.parse import quote_plus

from src.domain.configs.app_env import AppEnv


def read_secret_or_env(
    secret_name: str,
    env: str,
    default: str = "",
) -> str:
    """
    Приоритет: /run/secrets/<secret_name> → os.getenv(env) → default.
    Docker Swarm кладёт секреты в /run/secrets/ по имени секрета,
    не по значению env-переменной. Поэтому secret_name и env — разные параметры.
    """
    path = Path(f"/run/secrets/{secret_name}")
    if path.exists():
        return path.read_text().strip()
    return os.getenv(env, default)


def build_db_url(app_env: AppEnv) -> str:
    user = read_secret_or_env("postgres_user", "POSTGRES_USER", "postgres")
    password = read_secret_or_env("postgres_password", "POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")

    match app_env:
        case AppEnv.local | AppEnv.test:
            db = os.getenv("POSTGRES_DB_TEST", "postgres_test_01")
        case AppEnv.prod:
            db = os.getenv("POSTGRES_DB_PROD", "postgres_prod_01")
        case _:
            raise ValueError(f"Unknown AppEnv: {app_env}")

    return (
        f"postgresql+asyncpg://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{db}"
    )


def build_db_test_url() -> str:
    return build_db_url(
        app_env=AppEnv.test,
    )


def build_redis_url(db: int = 0) -> str:
    password = read_secret_or_env("redis_password", "REDIS_PASSWORD", "")
    host = os.getenv("REDIS_HOST", "redis")
    port = os.getenv("REDIS_PORT", "6379")
    return f"redis://:{password}@{host}:{port}/{db}"


def read_secret_bytes(secret_name: str) -> bytes:
    """
    Читает бинарный Docker Secret без strip.
    Используется для PEM-ключей и других бинарных данных.
    """
    path = Path(f"/run/secrets/{secret_name}")
    if not path.exists():
        raise FileNotFoundError(f"Docker Secret not found: {secret_name}")
    return path.read_bytes()
