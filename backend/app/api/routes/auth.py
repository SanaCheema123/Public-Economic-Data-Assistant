from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.models.entities import Session as UserSession, User
from app.schemas.auth import AuthResponse, LoginRequest, PasswordChange, PreferenceUpdate, ProfileUpdate, RegisterRequest, UserOut
from app.security.dependencies import get_current_user
from app.security.passwords import hash_password, verify_password
from app.security.tokens import create_access_token, create_refresh_token, decode_token, token_hash
from app.services.audit import audit

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id, full_name=user.full_name, email=user.email,
        preferred_language=user.preferred_language, theme_preference=user.theme_preference,
        notification_preference=user.notification_preference, ai_preference=user.ai_preference,
    )


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    response.set_cookie(
        "access_token", access, httponly=True, secure=settings.cookie_secure,
        samesite="lax", max_age=settings.access_token_minutes * 60, path="/",
    )
    response.set_cookie(
        "refresh_token", refresh, httponly=True, secure=settings.cookie_secure,
        samesite="lax", max_age=settings.refresh_token_days * 86400, path="/",
    )


def _create_session(db: Session, user: User, request: Request) -> tuple[str, str]:
    session = UserSession(
        user_id=user.id,
        refresh_token_hash="pending",
        user_agent=request.headers.get("user-agent", "")[:512],
        ip_address=request.client.host if request.client else None,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days),
    )
    db.add(session)
    db.flush()
    refresh = create_refresh_token(user.id, session.id)
    session.refresh_token_hash = token_hash(refresh)
    access = create_access_token(user.id)
    return access, refresh


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=email, full_name=payload.full_name.strip(), password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    access, refresh = _create_session(db, user, request)
    audit(db, "auth.register", user.id, getattr(request.state, "request_id", None))
    db.commit()
    _set_auth_cookies(response, access, refresh)
    return AuthResponse(user=_user_out(user), message="Account created")


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    access, refresh = _create_session(db, user, request)
    audit(db, "auth.login", user.id, getattr(request.state, "request_id", None))
    db.commit()
    _set_auth_cookies(response, access, refresh)
    return AuthResponse(user=_user_out(user), message="Signed in")


@router.post("/refresh", response_model=AuthResponse)
def refresh_session(response: Response, refresh_token: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh session is missing")
    try:
        payload = decode_token(refresh_token, "refresh")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Refresh session is invalid or expired")
    session = db.get(UserSession, payload.get("sid"))
    user = db.get(User, payload.get("sub"))
    expires_at = session.expires_at if session else None
    # SQLite drops timezone information even when the model column is timezone-aware.
    # Normalize defensively so the same refresh logic behaves consistently in tests,
    # local SQLite development, and PostgreSQL production deployments.
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not session or not user or session.revoked_at or not expires_at or expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh session is unavailable")
    if session.refresh_token_hash != token_hash(refresh_token):
        raise HTTPException(status_code=401, detail="Refresh session does not match")
    new_refresh = create_refresh_token(user.id, session.id)
    session.refresh_token_hash = token_hash(new_refresh)
    access = create_access_token(user.id)
    db.commit()
    _set_auth_cookies(response, access, new_refresh)
    return AuthResponse(user=_user_out(user), message="Session refreshed")


@router.post("/logout")
def logout(response: Response, refresh_token: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    if refresh_token:
        try:
            payload = decode_token(refresh_token, "refresh")
            session = db.get(UserSession, payload.get("sid"))
            if session:
                session.revoked_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            db.rollback()
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Signed out"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.patch("/me", response_model=UserOut)
def update_profile(payload: ProfileUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    email = payload.email.lower().strip()
    existing = db.scalar(select(User).where(User.email == email, User.id != user.id))
    if existing:
        raise HTTPException(status_code=409, detail="Email is already in use")
    user.full_name = payload.full_name.strip()
    user.email = email
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.patch("/preferences", response_model=UserOut)
def update_preferences(payload: PreferenceUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    for field in ("preferred_language", "theme_preference", "notification_preference", "ai_preference"):
        value = getattr(payload, field)
        if value is not None:
            setattr(user, field, value)
    db.commit(); db.refresh(user)
    return _user_out(user)


@router.post("/change-password")
def change_password(payload: PasswordChange, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    sessions = db.scalars(select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))).all()
    now = datetime.now(timezone.utc)
    for session in sessions:
        session.revoked_at = now
    db.commit()
    return {"message": "Password changed. Please sign in again."}
