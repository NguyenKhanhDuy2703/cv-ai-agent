"""
Service-to-service Bearer Key Authentication for Render Backend -> AI Agent communication.
Ensures agent only accepts authorized calls from backend services, never raw browser cookies.
"""
from fastapi import Header, HTTPException, status
from ..config import settings


async def verify_service_bearer(
    authorization: str = Header(default=None, alias="Authorization"),
):
    # If no secret key configured on agent (local development / testing), pass
    if not settings.ai_secret_key:
        return True

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Must be 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    if token != settings.ai_secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True
