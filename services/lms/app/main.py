from app.core.env import load_env
load_env()
# Initialize structured logging early
from app.core.logging import configure_logging
configure_logging()

from fastapi import FastAPI, Depends, APIRouter
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
import time
import datetime
from dotenv import load_dotenv
from app.db.deps import get_db

# Import routers from modules
from app.modules.auth.routes import router as auth_router
from app.modules.courses.routes import router as courses_router
from app.modules.courses.upload_routes import router as upload_router
from app.modules.enrollments.routes import router as enrollments_router
from app.modules.progress.routes import router as progress_router

app = FastAPI(title="smartCourse API")
load_dotenv()
# Record process start time for uptime reporting
_START_TIME = time.time()

# Create main API router
api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(courses_router)
api_router.include_router(upload_router)
api_router.include_router(enrollments_router)
api_router.include_router(progress_router)

app.include_router(api_router, prefix="/api/v1")
@app.get("/health")
async def health():
    """Simple health endpoint returning status, uptime, and timestamp."""
    uptime = time.time() - _START_TIME
    payload = {
        "status": "ok",
        "uptime_seconds": round(uptime, 2),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
    return JSONResponse(content=payload)


@app.get("/db/health")
def db_health_sa(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"db": "ok"}


# Add process logger
from app.core.logging import get_logger
logger = get_logger(__name__)

logger.info("fastapi process started")