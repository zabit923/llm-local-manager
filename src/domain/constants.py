import pytz

TIMEZONE = pytz.UTC
GENERAL_ERROR_MESSAGE = (
    ":=GCE| Model={model}, id={id}, text={text}, error={error}"
)

NONCE_SIZE = 12
VERSION_PREFIX = b"v1:"

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

IP_MAX_LEN = 45
USER_AGENT_MAX_LEN = 512

PORTAL_TOKEN_BYTE_LEN = 32

USED_TOTP_TTL_SEC = 90

BACKUP_CODE_LEN = 8
