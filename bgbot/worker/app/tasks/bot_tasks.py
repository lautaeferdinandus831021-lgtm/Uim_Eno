import json, logging, threading
from worker.app.celery_app import celery_app
from worker.app.config import worker_settings

logger = logging.getLogger("bgbot.worker.tasks")
_active_bots = {}
_bots_lock = threading.Lock()


def _get_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    url = worker_settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")
    engine = create_engine(url)
    return sessionmaker(bind=engine)()


def _get_redis():
    import redis
    return redis.from_url(worker_settings.REDIS_URL, decode_responses=True)


@celery_app.task(name="worker.app.tasks.bot_tasks.start_bot")
def start_bot(user_id):
    from worker.app.consumers.bot_consumer import BotConsumer
    uid = int(user_id)
    with _bots_lock:
        if uid in _active_bots and _active_bots[uid].running:
            return {"ok": False, "msg": "Already running"}
        consumer = BotConsumer(uid, _get_db, _get_redis())
        _active_bots[uid] = consumer
    consumer.start()
    return {"ok": True, "msg": "Bot started"}


@celery_app.task(name="worker.app.tasks.bot_tasks.stop_bot")
def stop_bot(user_id):
    uid = int(user_id)
    with _bots_lock:
        if uid in _active_bots:
            _active_bots[uid].stop()
            del _active_bots[uid]
            return {"ok": True}
    return {"ok": False, "msg": "Not running"}


@celery_app.task(name="worker.app.tasks.bot_tasks.update_all_positions")
def update_all_positions():
    with _bots_lock:
        bots = list(_active_bots.items())
    for uid, consumer in bots:
        if consumer.running:
            try: consumer.update_positions()
            except Exception: pass
    return {"updated": len(bots)}
