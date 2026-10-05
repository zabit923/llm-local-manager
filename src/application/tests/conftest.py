from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.tests.fake_ioc import _TestProvider
from src.domain.models.base import Base
from src.domain.ports.db.commiter import Commiter
from src.entrypoint.config.build import settings
from src.entrypoint.config.setup_db import AppDataBase
from src.entrypoint.ioc import setup_di
from src.entrypoint.main import create_app
from src.infrastructure.implementation.db.commiter import CommiterImpl


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(name="test_database")
async def database_resource() -> AsyncIterator[AppDataBase]:
    config = settings.db.model_copy(
        update={
            "url": settings.db.test_url,
            "pool_size": 2,
            "max_overflow": 2,
        }
    )
    database = AppDataBase(config)
    try:
        yield database
    finally:
        await database.dispose()


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db(test_database: AppDataBase):
    async with test_database.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        async with test_database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(name="test_db_session")
async def database_session(
    test_database: AppDataBase,
) -> AsyncIterator[AsyncSession]:
    async with test_database.session_factory() as session:
        yield session


@pytest_asyncio.fixture(name="app_with_test_db")
async def test_application(
    test_db_session: AsyncSession,
) -> AsyncIterator[FastAPI]:
    container = setup_di(_TestProvider(test_db_session))
    app = create_app(container=container)
    try:
        yield app
    finally:
        await container.close()


@pytest_asyncio.fixture
async def async_client(app_with_test_db: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app_with_test_db),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def commiter(test_db_session: AsyncSession) -> Commiter:
    return CommiterImpl(session=test_db_session)
