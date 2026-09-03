# LOCATION: backend/app/services/storage_service.py
"""
storage_service.py
==================
Storage abstraction layer for CogniSphere.
Decouples document file persistence from ephemeral container environments (like Render).
Provides a unified interface: save, read, delete, and check file existence.
Defaults to local disk storage with automatic parent directory creation and filename sanitization.
Can be swapped for AWS S3, Cloudflare R2, or Supabase Storage in the future.
"""

from __future__ import annotations
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BaseStorageBackend(ABC):
    """Abstract protocol for file persistence."""

    @abstractmethod
    def save_file(self, filename: str, file_bytes: bytes) -> str:
        """Save file bytes and return the resolved local path or storage URI."""
        pass

    @abstractmethod
    def read_file(self, file_path: str) -> bytes:
        """Read and return file bytes."""
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """Delete file if it exists. Returns True if deleted."""
        pass

    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """Check whether a file exists in storage."""
        pass


class LocalStorageBackend(BaseStorageBackend):
    """
    Local filesystem storage backend.
    Saves to the configured upload directory (default: ./uploads).
    Sanitizes filenames to prevent path traversal.
    """

    def __init__(self, base_dir: Optional[str] = None):
        upload_path = base_dir or os.getenv("UPLOAD_DIR", "uploads")
        self.base_dir = Path(upload_path).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, filename: str) -> Path:
        # Strip directory components to avoid directory traversal
        clean_name = Path(filename).name
        if not clean_name:
            clean_name = "unnamed_file"
        return self.base_dir / clean_name

    def save_file(self, filename: str, file_bytes: bytes) -> str:
        target = self._safe_path(filename)
        target.write_bytes(file_bytes)
        return str(target)

    def read_file(self, file_path: str) -> bytes:
        p = Path(file_path)
        if not p.is_absolute():
            p = self.base_dir / p
        return p.read_bytes()

    def delete_file(self, file_path: str) -> bool:
        p = Path(file_path)
        if not p.is_absolute():
            p = self.base_dir / p
        if p.exists() and p.is_file():
            p.unlink()
            return True
        return False

    def file_exists(self, file_path: str) -> bool:
        p = Path(file_path)
        if not p.is_absolute():
            p = self.base_dir / p
        return p.exists() and p.is_file()


_default_storage: Optional[BaseStorageBackend] = None


def get_storage() -> BaseStorageBackend:
    """Returns the singleton storage backend instance."""
    global _default_storage
    if _default_storage is None:
        _default_storage = LocalStorageBackend()
    return _default_storage
