from app.celery_app import celery_app
import logging
from typing import Any, Mapping


logger = logging.getLogger("app.tasks.notification_tasks")


@celery_app.task(
    name="tasks.notification_tasks.notify_course_published",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def notify_course_published(self, payload: Mapping[str, Any]):
    # payload can be either the inner payload dict or the full published message
    course_id = None
    if isinstance(payload, Mapping):
        course_id = payload.get("course_id") or (payload.get("payload") or {}).get("course_id")

    if not course_id:
        logger.warning("notify_course_published missing course_id in payload=%s", payload)
        return

    # TODO: implement notification logic (find recipients, enqueue emails, etc.)
    logger.info("[NOTIFY] course published -> %s", course_id)
