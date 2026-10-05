from dishka.integrations import taskiq as taskiq_integrations
from taskiq import AsyncBroker, TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from src.application.tasks.register import register_tasks
from src.entrypoint.config.build import settings
from src.entrypoint.config.task_setup import create_broker
from src.entrypoint.ioc import setup_di


def create_taskiq_app() -> AsyncBroker:
    broker = create_broker(
        broker_url=settings.worker.broker_url,
        result_ex_time=settings.worker.result_ex_time,
    )
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
