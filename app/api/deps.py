from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from app.core.redis import get_redis


async def redis_client() -> AsyncGenerator[Redis, None]:
    client = await get_redis()
    yield client
