from celery import Celery
from worker.app.config import worker_settings

celery_app = Celery("bgbot_worker", broker=worker_settings.REDIS_URL, backend=worker_settings.REDIS_URL)
celery_app.conf.update(task_serializer="json", accept_content=["json"], result_serializer="json", timezone="UTC", enable_utc=True, task_track_started=True, task_acks_late=True, worker_prefetch_multiplier=1, task_soft_time_limit=300, task_time_limit=600, beat_schedule={"cleanup-sessions": {"task": "worker.app.tasks.cleanup_tasks.cleanup_expired", "schedule": 3600.0}, "update-positions": {"task": "worker.app.tasks.bot_tasks.update_all_positions", "schedule": 30.0}})

import worker.app.tasks.bot_tasks  # noqa: F401
import worker.app.tasks.backtest_tasks  # noqa: F401
import worker.app.tasks.cleanup_tasks  # noqa: F401
