# ðŸ“ LOCATION: backend/app/services/file_processor.py
"""
file_processor.py
=================
Low-level file processing utilities.
Detects file type, extracts raw text, validates files before pipeline.
Used by memory_pipeline.py and upload_routes.py.
"""

from __future__ import annotations
import os
import mimetypes
from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".jpg":  "image",
    ".jpeg": "image",
    ".png":  "image",
    ".webp": "image",
    ".bmp":  "image",
    ".gif":  "image",
    ".pdf":  "document",
    ".docx": "document",
    ".doc":  "document",
    ".txt":  "text",
    ".md":   "text",
    ".csv":  "text",
}

MAX_FILE_SIZE_MB = 50


def get_file_category(file_path: str) -> str:
    """Returns 'image', 'document', 'text', or 'unsupported'."""
    ext = Path(file_path).suffix.lower()
    return SUPPORTED_EXTENSIONS.get(ext, "unsupported")


def is_supported(file_path: str) -> bool:
    return get_file_category(file_path) != "unsupported"


def validate_file(file_path: str) -> tuple[bool, str]:
    """
    Validates a file before ingestion.
    Returns (is_valid, error_message).
    """
    path = Path(file_path)

    if not path.exists():
        return False, f"File not found: {file_path}"

    if not path.is_file():
        return False, f"Not a file: {file_path}"

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return False, f"File too large: {size_mb:.1f}MB (max {MAX_FILE_SIZE_MB}MB)"

    if not is_supported(file_path):
        return False, f"Unsupported file type: {path.suffix}"

    return True, ""


def extract_raw_text(file_path: str) -> str:
    """
    Dispatches to the correct extractor based on file type.
    Returns raw text string (may be empty).
    """
    category = get_file_category(file_path)
    ext = Path(file_path).suffix.lower()

    if category == "image":
        try:
            from vision.ocr import extract_text
            return extract_text(file_path)
        except Exception as e:
            print(f"[FileProcessor] OCR failed: {e}")
            return ""

    if ext == ".pdf":
        try:
            from document.pdf_reader import read_pdf
            return read_pdf(file_path)
        except Exception as e:
            print(f"[FileProcessor] PDF read failed: {e}")
            return ""

    if ext in (".docx", ".doc"):
        try:
            from document.docx_reader import read_docx
            return read_docx(file_path)
        except Exception as e:
            print(f"[FileProcessor] DOCX read failed: {e}")
            return ""

    if category == "text":
        try:
            return Path(file_path).read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"[FileProcessor] Text read failed: {e}")
            return ""

    return ""


def detect_objects_safe(file_path: str) -> list[str]:
    """Runs YOLO only on images. Returns empty list for non-images."""
    if get_file_category(file_path) != "image":
        return []
    try:
        from vision.object_detector import detect_objects
        return detect_objects(file_path) or []
    except Exception as e:
        print(f"[FileProcessor] Object detection failed: {e}")
        return []


def get_file_metadata(file_path: str) -> dict:
    """Returns a metadata dict for a file on disk."""
    path = Path(file_path)
    stat = path.stat()
    return {
        "name":       path.name,
        "stem":       path.stem,
        "extension":  path.suffix.lower(),
        "category":   get_file_category(file_path),
        "size_bytes": stat.st_size,
        "size_mb":    round(stat.st_size / (1024 * 1024), 3),
        "mime_type":  mimetypes.guess_type(file_path)[0] or "application/octet-stream",
    }


