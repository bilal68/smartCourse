from app.core.env import load_env
load_env()
from fastapi import FastAPI, Depends
from app.api.v1.routes import api_router
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
import time
import datetime
from dotenv import load_dotenv
from sqlalchemy import text
from app.db.deps import get_db

app = FastAPI(title="smartCourse API")
load_dotenv()
# Record process start time for uptime reporting
_START_TIME = time.time()

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