import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient, ASGITransport

from src.application.tests.setup.dishka import setup_test_app
from src.domain.ports.db.commiter import Commiter
from src.entrypoint.main import create_app
from src.entrypoint.config.setup_db import app_db_test, app_db
from src.domain.models.base import Base
from src.infrastructure.implementation.db.commiter import CommiterImpl


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """
    Глобальный event loop для всех async тестов (API и unit).
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function", autouse=True)
async def setup_test_db() -> AsyncGenerator:
    """
    Fixture для настройки тестовой базы данных перед тестами и очистки после.
    Создает и удаляет все таблицы базы данных.
    """
    async with app_db_test.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with app_db_test.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def async_client(app_with_test_db: FastAPI) -> AsyncClient:  # type:ignore
    """
    Fixture для создания асинхронного клиента HTTP с подключением к FastAPI приложению.
    Использует ASGITransport для взаимодействия с приложением.
    """
    transport = ASGITransport(app=app_with_test_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client  # type:ignore


@pytest_asyncio.fixture(scope="function")
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture для создания тестовой сессии базы данных.
    Обеспечивает корректное закрытие сессии после использования.
    """
    async with app_db_test.session_factory() as session:
        yield session
        await session.close()


@pytest_asyncio.fixture(scope="function")
async def app_with_test_db(test_db_session: AsyncSession) -> AsyncGenerator:
    """
    Подменяем зависимости приложения, включая Dishka.
    """
    app = create_app()
    setup_test_app(app, test_db_session)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    app.dependency_overrides[app_db.session_getter] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
def commiter(
    test_db_session: AsyncSession,
) -> Commiter:
    return CommiterImpl(session=test_db_session)
