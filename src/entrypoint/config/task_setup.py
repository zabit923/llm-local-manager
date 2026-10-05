from taskiq import AsyncBroker
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from src.entrypoint.config import task_constants as constants


def create_broker(
    broker_url: str,
    result_ex_time: int | None = None,
) -> AsyncBroker:
    result_options = (
        {"result_ex_time": result_ex_time} if result_ex_time is not None else {}
    )
    redis_async_result = RedisAsyncResultBackend(
        redis_url=broker_url,
        **result_options,
    )
    broker = RedisStreamBroker(
        url=broker_url,
        queue_name=constants.TASK_QUEUE,
        consumer_group_name=constants.TASK_CONSUMER_GROUP,
        idle_timeout=constants.TASK_IDLE_TIMEOUT_MS,
        xread_block=constants.TASK_READ_BLOCK_MS,
        xread_count=constants.TASK_READ_COUNT,
        maxlen=constants.TASK_STREAM_MAX_LENGTH,
        approximate=True,  # MAXLEN ~ — trim ленивый, без overhead
    ).with_result_backend(
        redis_async_result,
    )
    return broker
