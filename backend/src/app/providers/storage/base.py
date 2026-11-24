from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageProvider(ABC):
    @abstractmethod
    def upload_file(self, file_obj: BinaryIO, storage_key: str, content_type: str = "") -> str:
        """Upload a file and return the storage key or URI."""
        pass

    @abstractmethod
    def get_presigned_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Return a temporary signed URL to download the file."""
        pass

    @abstractmethod
    def file_exists(self, storage_key: str) -> bool:
        """Check if a file exists in storage."""
        pass

    @abstractmethod
    def download_file(self, storage_key: str) -> bytes:
        """Download and return raw file bytes from storage."""
        pass
