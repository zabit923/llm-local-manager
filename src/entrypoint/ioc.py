from collections.abc import AsyncIterator
from typing import AsyncIterable

from aiohttp import ClientSession, ClientTimeout, TCPConnector
import redis.asyncio as aioredis
from dishka import (
    AsyncContainer,
    Provider,
    Scope,
    from_context,
    make_async_container,
    provide,
)
from dishka.integrations.taskiq import TaskiqProvider
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from taskiq import AsyncBroker

# --- Domain ports ---
from src.domain.ports.db.commiter import Commiter
from src.domain.ports.db.repositories.dish_repository import DishRepository
from src.domain.ports.db.repositories.drink_repository import DrinkRepository
from src.domain.ports.db.repositories.order_item_repository import OrderItemRepository
from src.domain.ports.db.repositories.order_repository import OrderRepository
from src.domain.ports.encryption.signing_secret import SigningSecretEncryption
from src.domain.ports.redis.gateway import RedisGateway
from src.domain.types.redis import BrokerRedis, CacheRedis

# --- Application ---
from src.application.services.cart import CartService
from src.application.services.order_agent import OrderAgent
from src.application.use_cases.task import TaskManager
from src.application.use_cases.dishes import DishUseCases
from src.application.use_cases.drinks import DrinkUseCases
from src.application.use_cases.orders import OrderUseCases
from src.application.tasks.register import register_tasks
from src.infrastructure.implementation.db.commiter import CommiterImpl
from src.infrastructure.implementation.db.repositories.dish_repository import (
    SqlAlchemyDishRepository,
)
from src.infrastructure.implementation.db.repositories.drink_repository import (
    SqlAlchemyDrinkRepository,
)
from src.infrastructure.implementation.db.repositories.order_item_repository import (
    SqlAlchemyOrderItemRepository,
)
from src.infrastructure.implementation.db.repositories.order_repository import (
    SqlAlchemyOrderRepository,
)

# --- Entrypoint ---
from src.entrypoint.config.build import Settings, settings
from src.entrypoint.config.settings import AppEnv
from src.entrypoint.config.setup_db import app_db
from src.entrypoint.config.task_setup import create_broker
from src.infrastructure.implementation.encryption.signing_secret_aes_gcm import (
    AesGcmSecretEncryptionImpl,
)
from src.infrastructure.implementation.redis.gateway import RedisGatewayImpl


# =============================================================================
# ConfigProvider
# =============================================================================


class ConfigProvider(Provider):
    config = from_context(
        provides=Settings,
        scope=Scope.APP,
    )

    @provide(scope=Scope.APP)
    def app_env(
        self,
        config: Settings,
    ) -> AppEnv:
        return config.app_env


# =============================================================================
# SessionProvider
# =============================================================================


class SessionProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_session_maker(self) -> async_sessionmaker[AsyncSession]:
        return app_db.session_factory

    @provide(scope=Scope.REQUEST)
    async def provide_session(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> AsyncIterable[AsyncSession]:
        async with session_maker() as session:
            yield session

    sa_commiter = provide(
        CommiterImpl,
        scope=Scope.REQUEST,
        provides=Commiter,
    )


# =============================================================================
# BrokerProvider
# =============================================================================


class BrokerProvider(Provider):
    @provide(scope=Scope.APP)
    async def provide_broker(
        self,
        config: Settings,
    ) -> AsyncIterator[AsyncBroker]:
        broker = create_broker(broker_url=config.worker.broker_url)
        register_tasks(broker=broker)
        await broker.startup()
        try:
            yield broker
        finally:
            await broker.shutdown()


# =============================================================================
# RedisProvider
# =============================================================================


class RedisProvider(Provider):
    @provide(scope=Scope.APP)
    async def provide_broker_redis(
        self,
        config: Settings,
    ) -> AsyncIterator[BrokerRedis]:
        client = aioredis.from_url(config.worker.broker_url)
        try:
            yield BrokerRedis(client)
        finally:
            await client.aclose()

    @provide(scope=Scope.APP)
    async def provide_cache_redis(
        self,
        config: Settings,
    ) -> AsyncIterator[CacheRedis]:
        url = config.redis_cache.url
        client = aioredis.from_url(url)
        try:
            yield CacheRedis(client)
        finally:
            await client.aclose()

    redis_gateway = provide(
        RedisGatewayImpl,
        scope=Scope.APP,
        provides=RedisGateway,
    )


# =============================================================================
# PortalAuthProvider
# =============================================================================


# class PortalAuthProvider(Provider):
#     """
#     Portal merchant-user auth: password hashing, sessions, login-attempts,
#     CSRF, pre_auth (F4), TOTP replay guard (F4). APP-scope (stateless
#     сервисы с инжектом Redis-клиента и конфига).
#
#     Использует общий CacheRedis (DB 1) — namespace-изоляция через префикс
#     'portal:' в ключах, см. KeyBuilder.portal_*.
#
#     NOTE F4: TotpService consume'им из AdminAuthProvider (там провайдится
#     как APP scope). Dishka cross-provider lookup автоматически подтянет
#     тот же instance. Семантически TotpService generic (не admin-specific),
#     но рефактор переноса в общий provider — вне scope F4.
#     """
#
#     @provide(scope=Scope.APP)
#     def portal_auth_config(
#         self,
#         settings: Settings,
#     ) -> PortalAuthConfig:
#         # settings.portal_auth — готовый PortalAuthConfig из build.py
#         # (_make_portal_auth с env-зависимыми cookie-полями).
#         return settings.portal_auth
#
#     @provide(scope=Scope.APP)
#     def password_hasher(
#         self,
#         config: PortalAuthConfig,
#     ) -> PasswordHasher:
#         return BcryptPasswordHasherImpl(dummy_hash=config.dummy_hash)
#
#     @provide(scope=Scope.APP)
#     def session_service(
#         self,
#         config: PortalAuthConfig,
#         redis: CacheRedis,
#     ) -> PortalSessionService:
#         return PortalSessionServiceImpl(config=config, redis=redis)
#
#     @provide(scope=Scope.APP)
#     def login_attempts_service(
#         self,
#         config: PortalAuthConfig,
#         redis: CacheRedis,
#     ) -> LoginAttemptsService:
#         return LoginAttemptsServiceImpl(config=config, redis=redis)
#
#     @provide(scope=Scope.APP)
#     def csrf_service(
#         self,
#         settings: Settings,
#     ) -> CsrfService:
#         return CsrfServiceImpl(secret=settings.encryption.portal_csrf_secret)
#
#     @provide(scope=Scope.APP)
#     def pre_auth_store(
#         self,
#         config: PortalAuthConfig,
#         redis: CacheRedis,
#     ) -> PortalPreAuthStore:
#         return PortalPreAuthStoreImpl(config=config, redis=redis)
#
#     @provide(scope=Scope.APP)
#     def portal_totp_replay_guard(
#         self,
#         redis_gateway: RedisGateway,
#     ) -> PortalTotpReplayGuard:
#         return PortalTotpReplayGuardImpl(redis_gateway=redis_gateway)
#
#     # Use cases — REQUEST scope (зависят от AsyncSession через
#     # gateway/reader/audit_log/commiter, переинициализируются per-request).
#     portal_login_use_case = provide(
#         LoginMerchantUseCase,
#         scope=Scope.REQUEST,
#     )
#     portal_logout_use_case = provide(
#         LogoutMerchantUseCase,
#         scope=Scope.REQUEST,
#     )
#     portal_totp_verify_use_case = provide(
#         VerifyPortalTotpUseCase,
#         scope=Scope.REQUEST,
#     )
#     portal_backup_code_login_use_case = provide(
#         LoginPortalBackupCodeUseCase,
#         scope=Scope.REQUEST,
#     )


# =============================================================================
# AiohttpProvider
# =============================================================================


class AiohttpProvider(Provider):
    @provide(scope=Scope.APP)
    async def provide_aiohttp_session(self) -> AsyncIterator[ClientSession]:
        async with ClientSession(
            connector=TCPConnector(
                limit=20,
                ttl_dns_cache=300,
                ssl=True,
            ),
            timeout=ClientTimeout(total=30, connect=5),
        ) as session:
            yield session


# =============================================================================
# EncryptionProvider
# =============================================================================


class EncryptionProvider(Provider):
    @provide(scope=Scope.APP)
    def signing_secret_encryption(
        self,
        config: Settings,
    ) -> SigningSecretEncryption:
        return AesGcmSecretEncryptionImpl(
            key=config.encryption.signing_secret_key,
            nonce_size=config.encryption.nonce_size,
            version_prefix=config.encryption.version_prefix,
        )


# =============================================================================
# PaymentProvider
# =============================================================================


# class PaymentProvider(Provider):


# =============================================================================
# TaskProvider
# =============================================================================


class TaskProvider(Provider):
    task_manager = provide(
        TaskManager,
        scope=Scope.REQUEST,
    )


# =============================================================================
# TransactionProvider
# =============================================================================


# class TransactionProvider(Provider):
#     transaction_gateway = provide(
#         TransactionGatewayImpl,
#         scope=Scope.REQUEST,
#         provides=TransactionGateway,
#     )
#     transaction_reader = provide(
#         TransactionReaderImpl,
#         scope=Scope.REQUEST,
#         provides=TransactionReader,
#     )


# =============================================================================
# BalanceLedgerProvider
# =============================================================================


# class BalanceLedgerProvider(Provider):
#     balance_ledger_gateway = provide(
#         BalanceLedgerGatewayImpl,
#         scope=Scope.REQUEST,
#         provides=BalanceLedgerGateway,
#     )


# =============================================================================
# AuditLogProvider
# =============================================================================


# class AuditLogProvider(Provider):
#     audit_log_gateway = provide(
#         AuditLogGatewayImpl,
#         scope=Scope.REQUEST,
#         provides=AuditLogGateway,
#     )
#     audit_log_reader = provide(
#         AuditLogReaderImpl,
#         scope=Scope.REQUEST,
#         provides=AuditLogReader,
#     )
#     # /staff/audit-logs
#     list_audit_logs = provide(
#         ListAuditLogsUseCase,
#         scope=Scope.REQUEST,
#     )


# =============================================================================
# Repositories setup
# =============================================================================


class RepositoryProvider(Provider):
    dish_repository = provide(
        SqlAlchemyDishRepository,
        scope=Scope.REQUEST,
        provides=DishRepository,
    )
    drink_repository = provide(
        SqlAlchemyDrinkRepository,
        scope=Scope.REQUEST,
        provides=DrinkRepository,
    )
    order_item_repository = provide(
        SqlAlchemyOrderItemRepository,
        scope=Scope.REQUEST,
        provides=OrderItemRepository,
    )
    order_repository = provide(
        SqlAlchemyOrderRepository,
        scope=Scope.REQUEST,
        provides=OrderRepository,
    )


class ApplicationProvider(Provider):
    cart_service = provide(CartService, scope=Scope.REQUEST)
    dish_use_cases = provide(DishUseCases, scope=Scope.REQUEST)
    drink_use_cases = provide(DrinkUseCases, scope=Scope.REQUEST)
    order_use_cases = provide(OrderUseCases, scope=Scope.REQUEST)
    order_agent = provide(OrderAgent, scope=Scope.REQUEST)

# =============================================================================
# Container setup
# =============================================================================


def setup_di() -> AsyncContainer:
    return make_async_container(
        ConfigProvider(),
        SessionProvider(),
        BrokerProvider(),
        RedisProvider(),
        AiohttpProvider(),
        TaskiqProvider(),
        EncryptionProvider(),
        TaskProvider(),
        RepositoryProvider(),
        ApplicationProvider(),
        context={Settings: settings},
    )
