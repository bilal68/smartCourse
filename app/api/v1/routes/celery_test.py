from fastapi import APIRouter
from app.tasks.task import long_task
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/celery", tags=["Celery"])


@router.post("/test")
def trigger_task(seconds: int = 5):
    task = long_task.delay(seconds)
    logger.info("celery task submitted", task_id=task.id, seconds=seconds)

    return {
        "message": "Task submitted",
        "task_id": task.id,
    }
