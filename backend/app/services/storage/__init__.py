import shutil
from pathlib import Path
from typing import BinaryIO, Optional
from abc import ABC, abstractmethod

from app.core.config import settings


class StorageService(ABC):
    """Abstract storage service for media files."""

    @abstractmethod
    def save(self, key: str, content: BinaryIO) -> str:
        """Save content to storage and return the storage key."""
        raise NotImplementedError

    @abstractmethod
    def open(self, key: str) -> Optional[BinaryIO]:
        """Open a file for reading."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a file from storage."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a file exists in storage."""
        raise NotImplementedError

    def get_path(self, key: str) -> str:
        """Get the absolute filesystem path for a key."""
        raise NotImplementedError

    @abstractmethod
    def get_url(self, key: str) -> str:
        """Get a URL for accessing the file (for local storage, returns file:// URL)."""
        ...


class LocalStorageService(StorageService):
    """Local filesystem storage implementation."""

    def __init__(self, root: str = None):
        self.root = Path(root or settings.MEDIA_STORAGE_ROOT).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, key: str) -> Path:
        """Resolve the full path for a storage key, preventing path traversal."""
        full_path = (self.root / key).resolve()
        # Ensure the path is within the storage root
        try:
            full_path.relative_to(self.root)
        except ValueError:
            raise ValueError(f"Invalid storage key: {key}")
        return full_path


    def open(self, key: str) -> Optional[BinaryIO]:
        """Open a file for reading."""
        full_path = self._get_full_path(key)
        if not full_path.exists():
            return None
        return open(full_path, "rb")


    def exists(self, key: str) -> bool:
        """Check if a file exists."""
        full_path = self._get_full_path(key)
        return full_path.exists()

    def save(self, key: str, content: BinaryIO) -> str:
        full_path = self._get_full_path(key)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = full_path.with_name(f".{full_path.name}.uploading")
        try:
            with open(temporary_path, "wb") as output:
                shutil.copyfileobj(content, output, length=1024 * 1024)
                output.flush()
            temporary_path.replace(full_path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink(missing_ok=True)
        return key

    def delete(self, key: str) -> bool:
        full_path = self._get_full_path(key)
        if not full_path.exists():
            return False
        if not full_path.is_file():
            raise ValueError(f"Storage key is not a file: {key}")
        full_path.unlink()
        return True

    def get_url(self, key: str) -> str:
        return self._get_full_path(key).as_uri()

    def get_path(self, key: str) -> str:
        """Get the absolute filesystem path."""
        return str(self._get_full_path(key))




# Cloud Storage Imports
try:
    from app.services.storage.s3_storage import S3StorageService
    from app.services.storage.gdrive_storage import GoogleDriveStorageService

    class StorageManager:
        """
        Central storage manager that routes to the correct storage provider based on business logic.
        Currently defaulting to Google Drive (BYOS) to maintain $0 storage costs.
        """
        def __init__(self):
            self.s3 = S3StorageService()
            self.gdrive = GoogleDriveStorageService()
            

    storage_manager = StorageManager()
except ImportError:
    StorageManager = None  # Optional cloud providers are not required for local storage.

_local_storage = LocalStorageService()

def get_storage_service() -> StorageService:
    import os
    if os.environ.get('STORAGE_PROVIDER') == 'gdrive':
        from app.services.storage.gdrive_storage import GoogleDriveStorageService
        return GoogleDriveStorageService()
    return _local_storage

