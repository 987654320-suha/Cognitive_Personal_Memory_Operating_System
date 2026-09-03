# ðŸ“ LOCATION: backend/app/services/folder_indexer.py

"""
folder_indexer.py
=================

Builds an in-memory index of files in the watched directories.

Features:
- Recursive scanning of Desktop, Downloads, Documents and Pictures
- Supports PDF, DOCX, DOC, TXT and common image formats
- Excludes development/system folders
- Calculates a lightweight file hash
- Finds files that have not yet been ingested by CogniSphere
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from datetime import datetime


# ============================================================
# SUPPORTED FILE TYPES
# ============================================================

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".pdf",
    ".docx",
    ".doc",
    ".txt",
}


# ============================================================
# DIRECTORIES WATCHED BY COGNISPHERE
# ============================================================

WATCHED_DIRS = [
    Path.home() / "Desktop",
    Path.home() / "Downloads",
    Path.home() / "Documents",
    Path.home() / "Pictures",
]


# ============================================================
# DIRECTORIES TO EXCLUDE
# ============================================================

EXCLUDED_DIR_NAMES = {
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    "__pycache__",
    ".git",
    ".next",
    "dist",
    "build",
}


# ============================================================
# FILE HASH
# ============================================================

def _file_hash(
    path: Path,
    chunk_size: int = 65536,
) -> str:
    """
    Calculate MD5 hash of the first 64 KB of a file.

    Used as a lightweight identifier for deduplication.
    """

    h = hashlib.md5()

    try:
        with open(path, "rb") as f:
            h.update(f.read(chunk_size))

    except Exception:
        return ""

    return h.hexdigest()


# ============================================================
# INDEX ONE DIRECTORY
# ============================================================

def index_directory(
    directory: Path,
    recursive: bool = True,
) -> list[dict]:
    """
    Scan a directory for supported files.

    If recursive=True, all nested folders are scanned.
    """

    if not directory.exists():
        return []

    pattern = "**/*" if recursive else "*"

    entries: list[dict] = []

    for f in directory.glob(pattern):

        # ----------------------------------------------------
        # Skip files inside excluded directories
        # ----------------------------------------------------

        if any(
            part.lower() in EXCLUDED_DIR_NAMES
            for part in f.parts
        ):
            continue

        # ----------------------------------------------------
        # Skip directories
        # ----------------------------------------------------

        if not f.is_file():
            continue

        # ----------------------------------------------------
        # Skip unsupported extensions
        # ----------------------------------------------------

        if f.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        # ----------------------------------------------------
        # Read file metadata
        # ----------------------------------------------------

        try:

            stat = f.stat()

            entries.append(
                {
                    "name": f.name,
                    "path": str(f),
                    "extension": f.suffix.lower(),
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(
                        stat.st_mtime
                    ).isoformat(),
                    "hash": _file_hash(f),
                    "directory": str(directory),
                }
            )

        except Exception as e:

            print(
                f"[FolderIndexer] Error reading {f}: {e}"
            )

    return entries


# ============================================================
# BUILD COMPLETE INDEX
# ============================================================

def build_full_index(
    recursive: bool = True,
) -> dict:
    """
    Recursively scan all CogniSphere watched directories.

    Returns:

    {
        "total": int,
        "by_directory": {
            "/path": [...]
        },
        "all_files": [...]
    }
    """

    by_dir: dict[str, list[dict]] = {}

    all_files: list[dict] = []

    for watch_dir in WATCHED_DIRS:

        entries = index_directory(
            watch_dir,
            recursive=recursive,
        )

        by_dir[str(watch_dir)] = entries

        all_files.extend(entries)

        print(
            f"[FolderIndexer] {watch_dir}: "
            f"{len(entries)} supported files found"
        )

    print(
        f"[FolderIndexer] Total supported files: "
        f"{len(all_files)}"
    )

    return {
        "total": len(all_files),
        "by_directory": by_dir,
        "all_files": all_files,
    }


# ============================================================
# FIND UNINGESTED FILES
# ============================================================

def find_uningested_files() -> list[dict]:
    """
    Find supported files that are not yet present
    in the CogniSphere database.

    Existing memories are compared using their
    'source' field.
    """

    try:

        from app.services.database_service import (
            get_all_memories,
        )

        existing = {
            m.get("source", "")
            for m in get_all_memories()
            if m.get("source")
        }

    except Exception as e:

        print(
            f"[FolderIndexer] Could not load existing "
            f"memories: {e}"
        )

        existing = set()

    # --------------------------------------------------------
    # Recursively scan all watched directories
    # --------------------------------------------------------

    index = build_full_index(
        recursive=True
    )

    # --------------------------------------------------------
    # Compare discovered files against database
    # --------------------------------------------------------

    unindexed = [
        f
        for f in index["all_files"]
        if f["name"] not in existing
    ]

    print(
        f"[FolderIndexer] "
        f"{len(unindexed)} unindexed files found"
    )

    return unindexed


