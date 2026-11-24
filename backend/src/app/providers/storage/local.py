import shutil
from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings
from app.providers.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str = ""):
        settings = get_settings()
        self.base_dir = Path(base_dir or settings.LOCAL_STORAGE_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def upload_file(self, file_obj: BinaryIO, storage_key: str, content_type: str = "") -> str:
        target_path = self.base_dir / storage_key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as f:
            shutil.copyfileobj(file_obj, f)
        return storage_key

    def get_presigned_url(self, storage_key: str, expires_in: int = 3600) -> str:
        target_path = (self.base_dir / storage_key).resolve()
        return target_path.as_uri()

    def file_exists(self, storage_key: str) -> bool:
        return (self.base_dir / storage_key).exists()

    def download_file(self, storage_key: str) -> bytes:
        target_path = self.base_dir / storage_key
        if not target_path.exists():
            raise FileNotFoundError(f"Local storage file not found: {storage_key}")
        return target_path.read_bytes()
