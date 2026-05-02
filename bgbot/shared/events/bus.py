import json
import asyncio
import logging
from typing import Callable, Dict, List, Optional
import redis.asyncio as aioredis
import redis as sync_redis
from shared.events.types import Event, EventType
from shared.config import settings

logger = logging.getLogger("bgbot.events")


class EventBus:
    PREFIX = "bgbot:events"

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._sync_redis = None
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._running = False

    async def connect(self):
        self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    def connect_sync(self):
        self._sync_redis = sync_redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def publish(self, event: Event):
        channel = f"{self.PREFIX}:{event.type.value}"
        data = event.to_json()
        if self._redis:
            await self._redis.publish(channel, data)
        elif self._sync_redis:
            self._sync_redis.publish(channel, data)

    def publish_sync(self, event: Event):
        if not self._sync_redis:
            self.connect_sync()
        self._sync_redis.publish(f"{self.PREFIX}:{event.type.value}", event.to_json())

    def subscribe(self, event_type: EventType, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def listen(self):
        if not self._redis:
            await self.connect()
        self._running = True
        ps = self._redis.pubsub()
        await ps.psubscribe(f"{self.PREFIX}:*")
        try:
            async for message in ps.listen():
                if not self._running:
                    break
                if message["type"] != "pmessage":
                    continue
                try:
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    event = Event.from_dict(json.loads(data))
                    for handler in self._handlers.get(event.type, []):
                        result = handler(event)
                        if asyncio.iscoroutine(result):
                            await result
                except Exception as e:
                    logger.error(f"Event error: {e}")
        finally:
            await ps.unsubscribe()
            await ps.close()

    def stop(self):
        self._running = False

    async def close(self):
        self.stop()
        if self._redis:
            await self._redis.close()


event_bus = EventBus()
