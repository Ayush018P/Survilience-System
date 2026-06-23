"""
NeuroGuard AI - Auth API
=========================
POST /api/login  — Authenticate admin and return JWT
POST /api/logout — Blacklist current token
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.schemas.schemas import LoginRequest, TokenResponse
from backend.services.auth_service import (
    create_access_token,
    get_current_user,
    get_token_remaining_ttl,
    verify_admin_credentials,
    security_scheme,
)
from backend.services.redis_service import redis_service
from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Authenticate with admin credentials and receive a JWT token.

    - **username**: Admin username (default: admin)
    - **password**: Admin password (default: admin)
    """
    if not verify_admin_credentials(request.username, request.password):
        logger.warning(f"Failed login attempt for: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=request.username, role="admin")

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        role="admin",
    )


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    user: dict = Depends(get_current_user),
):
    """
    Logout by blacklisting the current JWT token in Redis.
    The token will be rejected on subsequent requests.
    """
    token = credentials.credentials
    ttl = get_token_remaining_ttl(token)

    if ttl > 0 and redis_service.is_connected:
        await redis_service.blacklist_token(token, ttl)

    logger.info(f"User {user['sub']} logged out (token blacklisted, TTL={ttl}s)")

    return {"message": "Logged out successfully", "detail": "Token has been revoked"}

