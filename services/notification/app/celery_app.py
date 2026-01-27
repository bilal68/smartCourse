from celery import Celery

celery_app = Celery(
    "notification-worker",
    broker="amqp://guest:guest@rabbitmq:5672//",
    backend="redis://redis:6379/2"
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Import tasks
from app.tasks import email_tasks, sms_tasks  # noqa

if __name__ == "__main__":
    celery_app.start()
