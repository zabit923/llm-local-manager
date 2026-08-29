from typing import Optional

from redis.typing import ExpiryT

from src.domain.types.redis import CacheRedis


class RedisGatewayImpl:
    def __init__(
        self,
        redis: CacheRedis,
    ) -> None:
        self._redis = redis

    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[ExpiryT] = None,
    ) -> None:
        await self._redis.set(
            name=key,
            value=value,
            ex=ex,
        )

    async def set_nx(
        self,
        key: str,
        value: str,
        ex: Optional[ExpiryT] = None,
    ) -> bool:
        result = await self._redis.set(
            name=key,
            value=value,
            nx=True,
            ex=ex,
        )
        return result is not None

    async def get(
        self,
        key: str,
    ) -> bytes | None:
        return await self._redis.get(name=key)

    async def delete(
        self,
        key: str,
    ) -> None:
        await self._redis.delete(key)

    async def exists(
        self,
        key: str,
    ) -> bool:
        return await self._redis.exists(key) == 1
