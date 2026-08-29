from typing import Optional, Protocol

from redis.typing import ExpiryT


class RedisGateway(Protocol):
    async def set(
        self,
        key: str,
        value: bytes | str,
        ex: Optional[ExpiryT] = None,
    ) -> None:
        raise NotImplementedError

    async def set_nx(
        self,
        key: str,
        value: bytes | str,
        ex: Optional[ExpiryT] = None,
    ) -> bool:
        raise NotImplementedError

    async def get(
        self,
        key: str,
    ) -> bytes | None:
        raise NotImplementedError

    async def delete(
        self,
        key: str,
    ) -> None:
        raise NotImplementedError

    async def exists(
        self,
        key: str,
    ) -> bool:
        raise NotImplementedError
