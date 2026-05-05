import os
import logging

logger = logging.getLogger("bgbot.redis")

REDIS_URL = os.environ.get("REDIS_URL", "")

# Try to connect, fallback to dummy if not available
try:
    if REDIS_URL:
        import redis.asyncio as aioredis
        redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    else:
        raise Exception("No REDIS_URL")
except Exception:
    logger.warning("Redis not available, using in-memory fallback")

    class DummyRedis:
        def __init__(self):
            self._data = {}
            self._pubsub_data = []

        async def ping(self):
            return True

        async def get(self, key):
            return self._data.get(key)

        async def set(self, key, value, ex=None):
            self._data[key] = value

        async def delete(self, key):
            self._data.pop(key, None)

        async def publish(self, channel, message):
            pass

        async def close(self):
            pass

        def pubsub(self):
            return DummyPubSub()

    class DummyPubSub:
        async def psubscribe(self, *args): pass
        async def unsubscribe(self): pass
        async def close(self): pass
        def listen(self):
            return iter([])

    redis_client = DummyRedis()


async def get_redis():
    return redis_client


async def cache_set(key, value, ttl=300):
    await redis_client.set(key, value)


async def cache_get(key):
    return await redis_client.get(key)


async def cache_delete(key):
    await redis_client.delete(key)
