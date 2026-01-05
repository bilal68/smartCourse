from app.core.env import load_env

load_env()

from celery import Celery
from app.core.config import settings
from datetime import timedelta

celery_app = Celery(
    "app",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["app.tasks"], force=True)

celery_app.conf.beat_schedule = {
    "publish-outbox-every-5-seconds": {
        "task": "app.tasks.outbox_tasks.publish_pending_outbox",
        "schedule": 5.0,
        "args": (50,),
    }
}
