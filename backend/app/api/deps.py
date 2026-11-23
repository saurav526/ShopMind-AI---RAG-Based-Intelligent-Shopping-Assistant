"""FastAPI authentication, RBAC, and rate limiting dependencies."""
# This module provides FastAPI dependencies for user authentication, role-based access control (RBAC), and rate limiting. It includes functions to enforce rate limits, retrieve the current user, and check for admin privileges, while logging security events using the AISecurityGuard.
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.security import decode_access_token, rate_limiter
from app.database.session import get_db
from app.models.models import User
from app.security.guardrails import AISecurityGuard

bearer_scheme = HTTPBearer(auto_error=False)


def enforce_rate_limit(request: Request, db: Session = Depends(get_db)) -> None:
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not rate_limiter.check_rate_limit(client_ip):
        AISecurityGuard.log_security_event(
            db=db,
            event_type="RATE_LIMIT_EXCEEDED",
            severity="MEDIUM",
            risk_category="OWASP LLM10: Unbounded Consumption",
            endpoint=str(request.url.path),
            user_id=None,
            ip_address=client_ip,
            payload_excerpt=f"Rate limit exceeded by {client_ip}",
            mitigation_action="Throttled request with HTTP 429 Too Many Requests",
            blocked=True,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait before sending more requests.",
        )


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not credentials or not credentials.credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    return user


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials or not credentials.credentials:
        AISecurityGuard.log_security_event(
            db=db,
            event_type="UNAUTHORIZED_ACCESS_ATTEMPT",
            severity="MEDIUM",
            risk_category="Authentication & Access Control",
            endpoint=str(request.url.path),
            user_id=None,
            ip_address=request.client.host if request.client else "127.0.0.1",
            payload_excerpt="Missing Bearer token on protected endpoint",
            mitigation_action="Rejected with HTTP 401 Unauthorized",
            blocked=True,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except HTTPException as exc:
        AISecurityGuard.log_security_event(
            db=db,
            event_type="INVALID_JWT_TOKEN",
            severity="HIGH",
            risk_category="Authentication & Access Control",
            endpoint=str(request.url.path),
            user_id=None,
            ip_address=request.client.host if request.client else "127.0.0.1",
            payload_excerpt=credentials.credentials[:48],
            mitigation_action="Rejected invalid or expired JWT with HTTP 401",
            blocked=True,
        )
        raise exc

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first() if user_id else None
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found or inactive.")
    return user


def get_admin_user(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if current_user.role != "admin":
        AISecurityGuard.log_security_event(
            db=db,
            event_type="RBAC_PRIVILEGE_VIOLATION",
            severity="HIGH",
            risk_category="Role-Based Access Control (RBAC)",
            endpoint=str(request.url.path),
            user_id=current_user.id,
            ip_address=request.client.host if request.client else "127.0.0.1",
            payload_excerpt=f"Non-admin user {current_user.email} attempted admin operation",
            mitigation_action="Blocked with HTTP 403 Forbidden",
            blocked=True,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges are required to access this resource.",
        )
    return current_user
