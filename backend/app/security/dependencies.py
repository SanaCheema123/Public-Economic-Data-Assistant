from __future__ import annotations

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
import jwt

from app.database.session import get_db
from app.models.entities import User
from app.security.tokens import decode_token


def _extract_token(authorization: str | None, access_token: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return access_token


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    access_token: str | None = Cookie(default=None),
) -> User:
    token = _extract_token(authorization, access_token)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = decode_token(token, "access")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is unavailable")
    return user


def get_optional_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    access_token: str | None = Cookie(default=None),
) -> User | None:
    token = _extract_token(authorization, access_token)
    if not token:
        return None
    try:
        payload = decode_token(token, "access")
        return db.get(User, payload.get("sub"))
    except Exception:
        return None
