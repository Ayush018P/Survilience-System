"""
NeuroGuard AI - Authentication Service
========================================
JWT-based authentication with static admin credentials.
Supports token creation, verification, and Redis-backed blacklisting.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.config import settings
from backend.services.redis_service import redis_service

logger = logging.getLogger(__name__)

# Password hashing context (for future extensibility with multiple users)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme for Swagger UI
security_scheme = HTTPBearer()


def verify_admin_credentials(username: str, password: str) -> bool:
    """
    Validate admin credentials against static config.
    In production, this would check a database with hashed passwords.
    """
    return (
        username == settings.ADMIN_USERNAME
        and password == settings.ADMIN_PASSWORD
    )


def create_access_token(
    subject: str,
    role: str = "admin",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The user identifier (username)
        role: User role (admin/operator)
        expires_delta: Custom expiration time

    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    logger.info(f"Access token created for: {subject} (expires: {expire})")
    return token


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_token_remaining_ttl(token: str) -> int:
    """Calculate remaining TTL in seconds for a token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        exp = payload.get("exp", 0)
        now = datetime.now(timezone.utc).timestamp()
        remaining = int(exp - now)
        return max(remaining, 0)
    except JWTError:
        return 0


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """
    FastAPI dependency: Extract and validate the current user from JWT.

    Usage:
        @router.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            print(user["sub"])  # username
            print(user["role"])  # admin/operator
    """
    token = credentials.credentials

    # Check Redis blacklist (if Redis is available)
    if redis_service.is_connected:
        is_blacklisted = await redis_service.is_token_blacklisted(token)
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

    payload = decode_token(token)

    # Validate required fields
    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "sub": username,
        "role": payload.get("role", "operator"),
    }


async def require_admin(
    user: dict = Depends(get_current_user),
) -> dict:
    """
    FastAPI dependency: Require admin role.

    Usage:
        @router.delete("/users/{id}")
        async def delete_user(user: dict = Depends(require_admin)):
            ...
    """
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
