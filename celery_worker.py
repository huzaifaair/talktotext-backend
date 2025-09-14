from celery import Celery
from config import Config

# 🔹 Celery init
celery = Celery(
    "talktotext",
    broker=Config.REDIS_URL,   # Redis as broker
    backend=Config.REDIS_URL,  # Redis as result backend
    include=["core.tasks"],    # Tasks register
)

# 🔹 Celery Config
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,  # retry if Redis not ready yet
)

@celery.task(name="health.check")
def health_check():
    """
    Simple test task to confirm Celery <-> Redis <-> Worker is working.
    """
    return {"status": "ok"}
