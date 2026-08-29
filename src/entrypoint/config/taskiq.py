from dishka.integrations import taskiq as taskiq_integrations
from taskiq import AsyncBroker, TaskiqScheduler
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker
from taskiq.schedule_sources import LabelScheduleSource

from src.entrypoint.config.build import settings
from src.entrypoint.ioc import setup_di
from src.application.tasks.register import register_tasks


def create_taskiq_app() -> AsyncBroker:
    redis_async_result = RedisAsyncResultBackend(
        redis_url=settings.worker.broker_url,
        result_ex_time=settings.worker.result_ex_time,
    )
    broker = RedisStreamBroker(
        url=settings.worker.broker_url,
        queue_name="payolin:tasks",
        consumer_group_name="payolin:workers",
        idle_timeout=300_000,
        xread_block=5_000,
        xread_count=10,
        maxlen=10_000,
        approximate=True,
    ).with_result_backend(redis_async_result)

    container = setup_di()
    taskiq_integrations.setup_dishka(
        container=container,
        broker=broker,
    )
    register_tasks(broker)
    return broker


def create_taskiq_scheduler() -> TaskiqScheduler:
    broker = create_taskiq_app()
    return TaskiqScheduler(
        broker=broker,
        sources=[LabelScheduleSource(broker=broker)],
    )
