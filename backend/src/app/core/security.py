import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

ph = PasswordHasher()


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def hash_token(token: str) -> str:
    """Compute sha256 hash of refresh token for database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_token() -> Tuple[str, str]:
    """Generate a high-entropy URL-safe refresh token and its sha256 hash."""
    raw_token = secrets.token_urlsafe(64)
    return raw_token, hash_token(raw_token)


def create_access_token(
    user_id: str,
    is_admin: bool,
    expires_delta: Optional[timedelta] = None,
) -> Tuple[str, int]:
    """Create a signed JWT access token. Returns (token, expires_in_seconds)."""
    settings = get_settings()
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    expire = datetime.now(timezone.utc) + delta
    expires_in = int(delta.total_seconds())

    payload: Dict[str, Any] = {
        "sub": user_id,
        "is_admin": is_admin,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token."""
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
