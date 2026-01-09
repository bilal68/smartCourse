# app/middleware/logging.py
"""
Logging middleware for request/response tracking.
"""

import time
from fastapi import Request
from app.core.logging import get_logger

logger = get_logger(__name__)


async def logging_middleware(request: Request, call_next):
    """
    Log all incoming requests and their response times.
    """
    start_time = time.time()
    
    # Log request
    logger.info(
        "request started",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None,
    )
    
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log response
    logger.info(
        "request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )
    
    return response
