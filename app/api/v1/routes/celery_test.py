from fastapi import APIRouter
from app.tasks.task import long_task

router = APIRouter(prefix="/celery", tags=["Celery"])


@router.post("/test")
def trigger_task(seconds: int = 5):
    task = long_task.delay(seconds)

    return {
        "message": "Task submitted",
        "task_id": task.id,
    }
