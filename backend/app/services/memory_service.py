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

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def ingest_uploaded_file(file_bytes: bytes, filename: str) -> dict:
    """Save upload to disk then run the full pipeline."""
    dest = UPLOAD_DIR / filename
    dest.write_bytes(file_bytes)
    return run_pipeline(str(dest), source_hint=Path(filename).stem.replace("_", " ").title())


def list_memories() -> list[dict]:
    return get_all_memories()


def get_memory(memory_id: int) -> dict | None:
    return get_memory_by_id(memory_id)


def remove_memory(memory_id: int) -> bool:
    return delete_memory(memory_id)


def load_memories():
    """Legacy alias used by older services."""
    return get_all_memories()


