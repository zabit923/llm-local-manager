from typing import NewType

import redis.asyncio as aioredis

BrokerRedis = NewType("BrokerRedis", aioredis.Redis)
CacheRedis = NewType("CacheRedis", aioredis.Redis)
