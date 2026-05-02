import redis.asyncio as aioredis
from shared.config import settings

redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis():
    return redis_client


async def cache_set(key, value, ttl=300):
    await redis_client.set(key, value, ex=ttl)


async def cache_get(key):
    return await redis_client.get(key)


async def cache_delete(key):
    await redis_client.delete(key)
