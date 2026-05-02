import json, logging
import redis as sync_redis
from worker.app.config import worker_settings

logger = logging.getLogger("bgbot.event_consumer")


def start_event_consumer():
    r = sync_redis.from_url(worker_settings.REDIS_URL, decode_responses=True)
    ps = r.pubsub()
    ps.psubscribe("user:*:control")
    logger.info("Event consumer started")
    for message in ps.listen():
        if message["type"] != "pmessage": continue
        channel = message["channel"]
        try: data = json.loads(message["data"])
        except Exception: continue
        uid = int(channel.split(":")[1])
        action = data.get("action")
        if action == "start":
            from worker.app.tasks.bot_tasks import start_bot
            start_bot.delay(uid)
        elif action == "stop":
            from worker.app.tasks.bot_tasks import stop_bot
            stop_bot.delay(uid)
        elif action == "get_state":
            from worker.app.tasks.bot_tasks import _active_bots
            if uid in _active_bots:
                r.publish(f"user:{uid}:events", json.dumps({"event": "state_update", "data": _active_bots[uid].state}))


if __name__ == "__main__":
    start_event_consumer()
