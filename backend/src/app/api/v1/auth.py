from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_token,
    verify_password,
)
from app.db.models import RefreshToken, User

settings = get_settings()
limiter = Limiter(key_func=get_remote_address, enabled=settings.APP_ENV == "production")
router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember: bool = False


class MembershipItem(BaseModel):
    department_id: str
    department_code: str
    department_name: str
    role_level: int


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_admin: bool
    is_active: bool
    memberships: List[MembershipItem]


class LoginResponse(BaseModel):
    access_token: str
    expires_in: int
    user: UserResponse


def build_user_response(user: User) -> UserResponse:
    memberships = [
        MembershipItem(
            department_id=str(m.department_id),
            department_code=m.department.code,
            department_name=m.department.name,
            role_level=m.role_level,
        )
        for m in user.memberships
    ]
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        is_active=user.is_active,
        memberships=memberships,
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/15minute")
def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Authenticate user with email and password.

    Rate-limited to 5 attempts per 15 minutes.
    Sets rotated httpOnly, SameSite=Strict refresh token cookie.
    """
    settings = get_settings()

    # Generic error message to prevent account enumeration
    invalid_credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
    )

    user = db.query(User).filter(User.email == body.email.lower().strip()).first()
    if not user or not user.is_active:
        raise invalid_credentials_exc

    if not verify_password(body.password, str(user.password_hash)):
        raise invalid_credentials_exc

    # 1. Issue access token
    access_token, expires_in = create_access_token(user_id=str(user.id), is_admin=bool(user.is_admin))

    # 2. Issue refresh token
    refresh_days = 30 if body.remember else settings.REFRESH_TOKEN_DAYS
    raw_refresh, token_h = create_refresh_token()
    refresh_expire = datetime.now(timezone.utc) + timedelta(days=refresh_days)

    db_token = RefreshToken(
        user_id=user.id,
        token_hash=token_h,
        expires_at=refresh_expire,
        revoked_at=None,
    )
    db.add(db_token)
    db.commit()

    # 3. Set httpOnly cookie (Secure relaxed on localhost only)
    is_secure = settings.APP_ENV != "local"
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=is_secure,
        samesite="strict",
        path="/api/v1/auth",
        max_age=refresh_days * 86400,
    )

    return LoginResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=build_user_response(user),
    )


@router.post("/refresh", response_model=LoginResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    """Rotate refresh token and issue a fresh access token."""
    settings = get_settings()
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    t_hash = hash_token(refresh_token)
    now = datetime.now(timezone.utc)

    db_token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == t_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,  # type: ignore[arg-type]
        )
        .first()
    )

    if not db_token or not db_token.user or not db_token.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Rotate token: revoke old one
    db_token.revoked_at = now  # type: ignore[assignment]

    # Issue new refresh token
    new_raw, new_hash = create_refresh_token()
    new_expire = now + timedelta(days=settings.REFRESH_TOKEN_DAYS)
    new_db_token = RefreshToken(
        user_id=db_token.user_id,
        token_hash=new_hash,
        expires_at=new_expire,
        revoked_at=None,
    )
    db.add(new_db_token)
    db.commit()

    # Issue new access token
    user = db_token.user
    access_token, expires_in = create_access_token(user_id=str(user.id), is_admin=user.is_admin)

    is_secure = settings.APP_ENV != "local"
    response.set_cookie(
        key="refresh_token",
        value=new_raw,
        httponly=True,
        secure=is_secure,
        samesite="strict",
        path="/api/v1/auth",
        max_age=settings.REFRESH_TOKEN_DAYS * 86400,
    )

    return LoginResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=build_user_response(user),
    )


@router.post("/logout")
def logout(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    """Revoke refresh token and clear cookie."""
    if refresh_token:
        t_hash = hash_token(refresh_token)
        db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == t_hash).first()
        if db_token and db_token.revoked_at is None:
            db_token.revoked_at = datetime.now(timezone.utc)  # type: ignore[assignment]
            db.commit()

    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return profile, active department memberships, and admin status for current user."""
    return build_user_response(current_user)
