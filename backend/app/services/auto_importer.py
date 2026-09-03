# ðŸ“ LOCATION: backend/app/services/auto_importer.py
"""
auto_importer.py
================
One-time bulk importer: scans a folder and ingests every supported
file through the CogniSphere memory pipeline.

Use case: first-time setup when you want to import your existing
Desktop / Documents / Pictures into CogniSphere all at once.

Usage:
    python -m app.services.auto_importer --dir ~/Documents
    python -m app.services.auto_importer --dir ~/Downloads --dry-run
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

from ai.memory_pipeline import run_pipeline

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp",
    ".pdf", ".docx", ".doc", ".txt",
}


def import_directory(
    directory: str | Path,
    recursive: bool = False,
    dry_run: bool = False,
    skip_existing: bool = True,
) -> dict:
    """
    Scan a directory and ingest all supported files.

    Returns:
        {
            "total_found": int,
            "ingested": int,
            "skipped": int,
            "errors": list[str],
        }
    """
    base = Path(directory).expanduser().resolve()
    if not base.exists():
        raise FileNotFoundError(f"Directory not found: {base}")

    pattern = "**/*" if recursive else "*"
    files = [
        f for f in base.glob(pattern)
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    print(f"[AutoImporter] Found {len(files)} supported files in {base}")

    ingested = 0
    skipped  = 0
    errors: list[str] = []

    # Load existing sources to skip duplicates
    existing_sources: set[str] = set()
    if skip_existing:
        try:
            from app.services.database_service import get_all_memories
            existing_sources = {m.get("source", "") for m in get_all_memories()}
        except Exception:
            pass

    for f in files:
        if skip_existing and f.name in existing_sources:
            print(f"  [skip] {f.name} (already ingested)")
            skipped += 1
            continue

        if dry_run:
            print(f"  [dry-run] would ingest: {f.name}")
            ingested += 1
            continue

        try:
            result = run_pipeline(str(f))
            print(f"  [ok] {result.get('title', f.name)} â†’ goals: {result.get('detected_goals', [])}")
            ingested += 1
        except Exception as e:
            msg = f"{f.name}: {e}"
            print(f"  [error] {msg}")
            errors.append(msg)

    return {
        "total_found": len(files),
        "ingested": ingested,
        "skipped": skipped,
        "errors": errors,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk import files into CogniSphere")
    parser.add_argument("--dir",       required=True, help="Directory to import")
    parser.add_argument("--recursive", action="store_true", help="Scan subdirectories")
    parser.add_argument("--dry-run",   action="store_true", help="Preview without importing")
    args = parser.parse_args()

    summary = import_directory(args.dir, recursive=args.recursive, dry_run=args.dry_run)
    print(f"\n[AutoImporter] Summary: {summary}")


