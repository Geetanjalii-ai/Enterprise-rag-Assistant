from app.core.config import get_settings
from app.core.security import hash_password, verify_password


def test_settings_loaded():
    settings = get_settings()
    assert settings.APP_ENV in ["local", "development", "production"]
    assert settings.QDRANT_COLLECTION == "enterprise_docs"
    assert settings.EMBEDDING_DIM == 1024


def test_password_hashing():
    pw = "SecureP@ssword123"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
