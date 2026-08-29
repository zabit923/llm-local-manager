from taskiq import AsyncBroker
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker


def create_broker(broker_url: str) -> AsyncBroker:
    redis_async_result = RedisAsyncResultBackend(
        redis_url=broker_url,
    )
    broker = RedisStreamBroker(
        url=broker_url,
        queue_name="payolin:tasks",
        consumer_group_name="payolin:workers",
        idle_timeout=300_000,  # 5 минут в ms: после этого PEL-запись
        xread_block=5_000,  # воркер блокируется на 5 сек ожидая задачи
        xread_count=10,  # берёт до 10 задач за один XREADGROUP
        maxlen=10_000,  # ограничение длины стрима (AОF не резиновый)
        approximate=True,  # MAXLEN ~ — trim ленивый, без overhead
    ).with_result_backend(
        redis_async_result,
    )
    return broker
