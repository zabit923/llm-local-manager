from fastapi import FastAPI
from dishka.integrations.fastapi import setup_dishka
from dishka import make_async_container
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.tests.fake_ioc import _TestProvider


def setup_test_app(
    app: FastAPI,
    test_session: AsyncSession,
) -> None:
    test_provider = _TestProvider(test_session)
    container = make_async_container(test_provider)
    setup_dishka(container=container, app=app)
