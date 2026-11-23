from app.core.config import get_settings
from app.providers.storage.b2 import B2StorageProvider
from app.providers.storage.base import StorageProvider
from app.providers.storage.local import LocalStorageProvider


def get_storage_provider() -> StorageProvider:
    settings = get_settings()
    if settings.STORAGE_BACKEND == "b2":
        return B2StorageProvider()
    return LocalStorageProvider()


__all__ = ["StorageProvider", "B2StorageProvider", "LocalStorageProvider", "get_storage_provider"]
