from app.celery_app import celery_app
import logging
from typing import Any, Mapping
from app.integrations.kafka.producer import emit_verification_email_event


logger = logging.getLogger("app.tasks.notification_tasks")


@celery_app.task(name="tasks.notification_tasks.send_verification_email")
def send_verification_email(user_id: str, email: str, token: str):
    # Emit Kafka event for verification email
    emit_verification_email_event(user_id=user_id, email=email, token=token)
    # Notification service will consume and send the actual email
