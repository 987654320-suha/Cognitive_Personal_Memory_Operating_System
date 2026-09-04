# LOCATION: backend/app/auth/deps.py
"""
deps.py
=======
FastAPI authentication dependencies for protecting endpoints and extracting current user.
"""

from __future__ import annotations
from typing import Optional
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from database.database import get_db
from app.models.user import User
from app.auth.security import decode_access_token

COOKIE_NAME = "access_token"
COOKIE_MAX_AGE = 7 * 24 * 3600  # 7 days in seconds


def set_auth_cookie(response: Response, token: str) -> None:
    """Sets a secure HTTP-only cookie with cross-site SameSite=None support."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="none",
        secure=True,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    """Clears the authentication cookie."""
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        samesite="none",
        secure=True,
    )


def extract_token_from_request(request: Request) -> Optional[str]:
    """Extracts JWT token from cookie or Authorization header."""
    # 1. Preferred: HTTP-only cookie
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token

    # 2. Fallback: Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency that enforces authentication.
    Raises HTTP 401 if token is missing, invalid, or user does not exist.
    """
    token = extract_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication session.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication session subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Dependency that returns the authenticated User if valid token is provided,
    or None if unauthenticated (without raising an exception).
    """
    token = extract_token_from_request(request)
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None

    try:
        user_id = int(payload["sub"])
        return db.query(User).filter(User.id == user_id).first()
    except (ValueError, TypeError):
        return None
