import asyncio
import logging
from collections.abc import Awaitable, Callable

from dishka import AsyncContainer

from src.domain.types.model_id_uuid import ModelIdUuidType
from src.entrypoint.config.build import settings
from src.entrypoint.config.setup_db import app_db
from src.entrypoint.ioc import setup_di
from src.entrypoint.logging.setup import setup_logging

setup_logging(app_env=settings.app_env)

logger = logging.getLogger(__name__)


# async def run_worker() -> None:
#     from src.entrypoint.logging import setup  # noqa: F401
#
#     logger.info("OutboxListener worker starting")
#
#     container = setup_di()
#     task_factory = make_task_factory(container=container)
#     merchant_webhook_task_factory = make_merchant_webhook_task_factory(
#         container=container,
#     )
#
#     try:
#         listener = OutboxListener(
#             task_factory=task_factory,
#             dsn=settings.db.asyncpg_url,
#             channel=OUTBOX_NOTIFY_CHANNEL,
#             config=settings.outbox,
#             max_concurrent=settings.outbox.max_concurrent_tasks,
#         )
#         merchant_webhook_listener = MerchantWebhookListener(
#             task_factory=merchant_webhook_task_factory,
#             dsn=settings.db.asyncpg_url,
#             channel=MERCHANT_WEBHOOK_OUTBOX_NOTIFY_CHANNEL,
#             config=settings.outbox,
#             max_concurrent=settings.outbox.max_concurrent_tasks,
#         )
#         await asyncio.gather(
#             listener.listen(),
#             merchant_webhook_listener.listen(),
#             reconciliation_loop(
#                 container=container,
#                 task_factory=task_factory,
#             ),
#             merchant_registry_reconcile_loop(
#                 container=container,
#             ),
#             balance_reconcile_loop(
#                 container=container,
#             ),
#             merchant_webhook_reconcile_loop(
#                 container=container,
#                 task_factory=merchant_webhook_task_factory,
#             ),
#         )
#     finally:
#         await container.close()
#         await app_db.dispose()
#         logger.info("OutboxListener worker stopped")
