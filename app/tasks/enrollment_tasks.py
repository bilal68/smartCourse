from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.enrollment import Enrollment
import time


@celery_app.task(
    name="app.tasks.enrollment_tasks.handle_enrollment_post_actions",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=5,
    retry_kwargs={"max_retries": 3},
)
def handle_enrollment_post_actions(self, enrollment_id: str):
    db = SessionLocal()
    try:
        enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
        if not enrollment:
            return

        time.sleep(3)
        print(f"[CELERY] Post enrollment actions done for {enrollment_id}")

    finally:
        db.close()
