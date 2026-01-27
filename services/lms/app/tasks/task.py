import time
from app.celery_app import celery_app

@celery_app.task(bind=True)
def long_task(self, seconds: int):
    time.sleep(seconds)
    return {
        "status": "completed",
        "slept_for": seconds,
    }
