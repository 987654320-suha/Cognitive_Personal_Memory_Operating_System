# LOCATION: backend/app/routes/upload_routes.py
"""
upload_routes.py
================
Document and image upload endpoint.
Uses Starlette run_in_threadpool to execute heavy CPU/model pipelines off the
async event loop, preventing event-loop freezing and 502 Bad Gateway timeouts.
"""

from __future__ import annotations
import os
import time
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from starlette.concurrency import run_in_threadpool

from app.services.memory_service import ingest_uploaded_file
from ai.embedding_service import is_model_loaded, MODEL_NAME

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".txt", ".md", ".csv",
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif",
}

ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/octet-stream",  # Fallback sent by many browsers for binary/doc formats
}

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


@router.get("/status")
def upload_service_status():
    """
    Lightweight health/status check reporting AI readiness without
    loading heavy models into memory.
    """
    return {
        "status":               "ready",
        "embedding_model":      MODEL_NAME,
        "embedding_loaded":     is_model_loaded(),
        "max_file_size_mb":     50,
        "supported_extensions": sorted(list(ALLOWED_EXTENSIONS)),
    }


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a document or image file.
    Runs OCR → Embedding → SQLite → FAISS → GAMA in a threadpool worker
    to prevent event loop blocking and 502 proxy timeouts on Render.
    """
    t_start = time.perf_counter()
    filename = file.filename or "uploaded_file"
    ext = Path(filename).suffix.lower()

    # Content type & extension validation
    if ext not in ALLOWED_EXTENSIONS and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}' (content-type: {file.content_type}). Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    try:
        file_bytes = await file.read()
    except Exception as read_err:
        print(f"[Upload Error] Failed reading upload payload for {filename}: {read_err}")
        raise HTTPException(status_code=400, detail="Could not read uploaded file data.")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        size_mb = len(file_bytes) / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"File size ({size_mb:.1f} MB) exceeds maximum allowed limit of 50 MB.",
        )

    print(f"[UPLOAD RECEIVED] {filename} ({len(file_bytes) / 1024:.1f} KB, mime: {file.content_type})")

    # Run heavy ingestion off the asyncio loop to keep the server 100% responsive!
    try:
        result = await run_in_threadpool(ingest_uploaded_file, file_bytes, filename)
        elapsed = time.perf_counter() - t_start
        print(f"[UPLOAD SUCCESS] {filename} ingested in {elapsed:.3f}s (Memory #{result.get('id')})")
        return {
            "success":         True,
            "memory":          result,
            "processing_time": round(elapsed, 3),
        }

    except Exception as e:
        elapsed = time.perf_counter() - t_start
        print(f"[UPLOAD FAILED] {filename} error after {elapsed:.3f}s: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}",
        )
