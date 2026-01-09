# app/middleware/auth.py
"""
Authentication middleware for validating JWT tokens.
Can be used to add request-level auth context.
"""

from fastapi import Request, HTTPException, status
from jose import JWTError
from app.core.security import decode_access_token


async def auth_middleware(request: Request, call_next):
    """
    Middleware to validate JWT tokens on every request.
    Currently implemented via Depends() in routes.
    This middleware can be used for global auth validation if needed.
    """
    # Skip auth for public endpoints
    if request.url.path in ["/health", "/db/health", "/docs", "/openapi.json"]:
        return await call_next(request)
    
    # Example: Extract and validate token from header
    # auth_header = request.headers.get("Authorization")
    # if auth_header and auth_header.startswith("Bearer "):
    #     token = auth_header.split(" ")[1]
    #     try:
    #         payload = decode_access_token(token)
    #         request.state.user_id = payload.get("sub")
    #     except JWTError:
    #         raise HTTPException(
    #             status_code=status.HTTP_401_UNAUTHORIZED,
    #             detail="Invalid authentication credentials",
    #         )
    
    response = await call_next(request)
    return response
