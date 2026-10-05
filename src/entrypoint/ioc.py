from collections.abc import AsyncIterator
from typing import AsyncIterable

import redis.asyncio as aioredis
from aiohttp import ClientSession, ClientTimeout, TCPConnector
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

from src.application.agent.contracts.ports import AgentModel, SessionStore
from src.application.agent.conversation.sessions import InMemorySessionStore
from src.application.agent.service import OrderAgent
from src.application.services.cart import CartService
from src.application.tasks.register import register_tasks
from src.application.use_cases.dishes import DishUseCases
from src.application.use_cases.drinks import DrinkUseCases
from src.application.use_cases.orders import OrderUseCases
from src.application.use_cases.task import TaskManager
from src.domain.ports.db.commiter import Commiter
from src.domain.ports.db.repositories.dish_repository import DishRepository
from src.domain.ports.db.repositories.drink_repository import DrinkRepository
from src.domain.ports.db.repositories.order_item_repository import (
    OrderItemRepository,
)
from src.domain.ports.db.repositories.order_repository import OrderRepository
from src.domain.ports.encryption.signing_secret import SigningSecretEncryption
from src.domain.ports.redis.gateway import RedisGateway
from src.domain.types.redis import BrokerRedis, CacheRedis
from src.entrypoint.config.build import Settings, settings
from src.entrypoint.config.settings import AppEnv
from src.entrypoint.config.setup_db import AppDataBase
from src.entrypoint.config.task_setup import create_broker
from src.infrastructure.implementation.db.commiter import CommiterImpl
from src.infrastructure.implementation.db.repositories import (
    SqlAlchemyDishRepository,
    SqlAlchemyDrinkRepository,
    SqlAlchemyOrderItemRepository,
    SqlAlchemyOrderRepository,
)
from src.infrastructure.implementation.encryption import (
    AesGcmSecretEncryptionImpl,
)
from src.infrastructure.implementation.llm.qwen import QwenAgentModel
from src.infrastructure.implementation.redis.gateway import RedisGatewayImpl


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


class SessionProvider(Provider):
    @provide(scope=Scope.APP)
    async def database(self, config: Settings) -> AsyncIterator[AppDataBase]:
        database = AppDataBase(config.db)
        try:
            yield database
        finally:
            await database.dispose()

    @provide(scope=Scope.APP)
    def provide_session_maker(
        self,
        database: AppDataBase,
    ) -> async_sessionmaker[AsyncSession]:
        return database.session_factory

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


class BrokerProvider(Provider):
    @provide(scope=Scope.APP)
    async def provide_broker(
        self,
        config: Settings,
    ) -> AsyncIterator[AsyncBroker]:
        broker = create_broker(broker_url=config.worker.broker_url)
        register_tasks(broker)
        await broker.startup()
        try:
            yield broker
        finally:
            await broker.shutdown()


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


class TaskProvider(Provider):
    task_manager = provide(
        TaskManager,
        scope=Scope.REQUEST,
    )


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

    @provide(scope=Scope.APP)
    def agent_model(self) -> AgentModel:
        return QwenAgentModel()

    session_store = provide(
        InMemorySessionStore,
        scope=Scope.APP,
        provides=SessionStore,
    )

    @provide(scope=Scope.REQUEST)
    def order_agent(
        self,
        dishes: DishUseCases,
        drinks: DrinkUseCases,
        orders: OrderUseCases,
        model: AgentModel,
        sessions: SessionStore,
    ) -> OrderAgent:
        return OrderAgent(dishes, drinks, orders, model, sessions)


def setup_di(*overrides: Provider) -> AsyncContainer:
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
        *overrides,
        context={Settings: settings},
    )
