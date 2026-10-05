from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.entrypoint.config.settings import DbSettings


class AppDataBase:
    def __init__(
        self,
        config: DbSettings,
    ):
        self.engine: AsyncEngine = create_async_engine(
            url=config.url,
            echo=config.echo,
            echo_pool=config.echo_pool,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            pool_pre_ping=config.pool_pre_ping,
            connect_args={
                "server_settings": {
                    "application_name": "payolin",
                },
                "command_timeout": 10,
            },
        )
        self.session_factory: async_sessionmaker[AsyncSession] = (
            async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
            )
        )

    async def dispose(self) -> None:
        await self.engine.dispose()

    async def session_getter(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            yield session
