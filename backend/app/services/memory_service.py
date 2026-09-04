"""
app/services/memory_service.py
================================
Service layer between FastAPI routes and the memory pipeline.
"""

from __future__ import annotations
import os
import shutil
from pathlib import Path
from sqlalchemy.orm import Session

from ai.memory_pipeline import run_pipeline
from app.services.database_service import get_all_memories, get_memory_by_id, delete_memory

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads")).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def ingest_uploaded_file(file_bytes: bytes, filename: str) -> dict:
    """Save upload to disk then run the full pipeline."""
    import time
    t0 = time.perf_counter()
    safe_filename = Path(filename).name
    dest = UPLOAD_DIR / safe_filename
    dest.write_bytes(file_bytes)
    print(f"[FILE SAVED] {safe_filename} ({len(file_bytes)/1024:.1f} KB) in {time.perf_counter() - t0:.3f}s")
    return run_pipeline(str(dest), source_hint=Path(safe_filename).stem.replace("_", " ").title())


def list_memories(user_id: int | None = None) -> list[dict]:
    return get_all_memories(user_id=user_id)


def get_memory(memory_id: int, user_id: int | None = None) -> dict | None:
    return get_memory_by_id(memory_id, user_id=user_id)


def remove_memory(memory_id: int, user_id: int | None = None) -> bool:
    return delete_memory(memory_id, user_id=user_id)


def load_memories(user_id: int | None = None):
    """Legacy alias used by older services."""
    return get_all_memories(user_id=user_id)


