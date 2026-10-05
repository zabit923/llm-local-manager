from typing import AsyncGenerator, AsyncIterator
from unittest.mock import AsyncMock, Mock

import redis.asyncio as aioredis
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import AsyncBroker


class _TestProvider(Provider):
    def __init__(self, test_session: AsyncSession):
        super().__init__()
        self._test_session = test_session

    @provide(scope=Scope.REQUEST, override=True)
    async def provide_session(self) -> AsyncGenerator[AsyncSession, None]:
        yield self._test_session

    @provide(scope=Scope.APP)
    def provide_redis(self) -> aioredis.Redis:
        """Mock Redis для тестов."""
        return AsyncMock(spec=aioredis.Redis)

    @provide(scope=Scope.APP, override=True)
    async def provide_broker(self) -> AsyncIterator[AsyncBroker]:
        """Mock AsyncBroker для тестов."""
        mock_broker = AsyncMock(spec=AsyncBroker)
        mock_task = AsyncMock()
        mock_task.kiq = AsyncMock()
        mock_broker.find_task = Mock(return_value=mock_task)
        yield mock_broker
