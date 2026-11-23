"""Security utilities: password hashing, JWT token management, RBAC dependencies, and rate limiting."""

import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import logger, settings

security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class RateLimiter:
    """Sliding-window rate limiter backed by Redis when available or in-memory fallback."""

    def __init__(self, max_requests: int = 90, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: Dict[str, List[float]] = defaultdict(list)

    def check_rate_limit(self, client_key: str, custom_limit: Optional[int] = None) -> bool:
        limit = custom_limit or self.max_requests
        now = time.time()
        window_start = now - self.window_seconds
        timestamps = [ts for ts in self._buckets[client_key] if ts > window_start]
        if len(timestamps) >= limit:
            self._buckets[client_key] = timestamps
            return False
        timestamps.append(now)
        self._buckets[client_key] = timestamps
        return True

    def reset(self) -> None:
        self._buckets.clear()


rate_limiter = RateLimiter(max_requests=settings.RATE_LIMIT_PER_MINUTE, window_seconds=60)
