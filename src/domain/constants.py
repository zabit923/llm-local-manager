import pytz


TIMEZONE = pytz.UTC
# TIMEZONE = pytz.timezone("Europe/Moscow")

NONCE_SIZE = 12
VERSION_PREFIX = b"v1:"

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

API_PREFIX: str = "/api"
APIV1_PREFIX: str = "/v1"
APIV1_AUTH: str = "/auth"
APIV1_PUB: str = "/pub"
APIV1_STAFF: str = "/staff"
APIV1_PORTAL: str = "/portal"

# portal
IP_MAX_LEN = 45
USER_AGENT_MAX_LEN = 512

PORTAL_TOKEN_BYTE_LEN = 32

# TOTP-код валиден в течение 3 временных окон:
#   previous (-30s) + current (0) + next (+30s, из-за valid_window=1 в verify).
# Значит код может быть успешно провалидирован в течение ~60-90 сек.
# TTL = 90 сек гарантированно перекрывает окно + запас на обработку.
# Это свойство TOTP-алгоритма (RFC 6238 + valid_window=1), не бизнес-параметр —
USED_TOTP_TTL_SEC = 90

# Длина backup-кода в hex символах. Совпадает с генерацией (F4.6 setup):
# secrets.token_hex(4) -> 8 символов = 32 бита энтропии.
BACKUP_CODE_LEN = 8
