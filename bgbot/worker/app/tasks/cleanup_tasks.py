import time, logging
from worker.app.celery_app import celery_app
from worker.app.config import worker_settings

logger = logging.getLogger("bgbot.worker.cleanup")


@celery_app.task(name="worker.app.tasks.cleanup_tasks.cleanup_expired")
def cleanup_expired():
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    url = worker_settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")
    engine = create_engine(url)
    Session = sessionmaker(bind=engine)
    db = Session()
    now = time.time()
    try:
        db.execute(text("DELETE FROM sessions WHERE expires_at < :now"), {"now": now})
        db.execute(text("DELETE FROM refresh_tokens WHERE expires_at < :now"), {"now": now})
        db.execute(text("DELETE FROM security_logs WHERE created_at < :cutoff"), {"cutoff": now - 2592000})
        db.commit()
        logger.info("Cleanup done")
    except Exception as e:
        logger.error(f"Cleanup: {e}")
    finally: db.close()
