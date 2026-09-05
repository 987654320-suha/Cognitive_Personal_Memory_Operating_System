# LOCATION: desktop_agent/parsers.py
"""
parsers.py
==========
Extensible parser registry and file filtering for CogniSphere Desktop Agent.
Determines which files are eligible for synchronization and handles unsupported
or temporary files safely.
"""

from __future__ import annotations
import os
import mimetypes
from pathlib import Path
from typing import Dict, Optional, Set, Type


# ── System / Temporary Blacklist ──────────────────────────────────────────────

EXCLUDED_FILENAMES: Set[str] = {
    "desktop.ini",
    "thumbs.db",
    ".ds_store",
    "icon\r",
}

EXCLUDED_EXTENSIONS: Set[str] = {
    ".tmp",
    ".temp",
    ".crdownload",
    ".part",
    ".lock",
    ".swp",
    ".bak",
    ".log",
}

EXCLUDED_DIR_NAMES: Set[str] = {
    ".git",
    ".svn",
    ".hg",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    "__pycache__",
    ".next",
    "dist",
    "build",
    "system volume information",
    "$recycle.bin",
}


# ── Parser Classes ────────────────────────────────────────────────────────────

class BaseParser:
    category: str = "general"
    extensions: Set[str] = set()

    @classmethod
    def can_parse(cls, path: Path) -> bool:
        return path.suffix.lower() in cls.extensions


class PDFParser(BaseParser):
    category = "document"
    extensions = {".pdf"}


class DOCXParser(BaseParser):
    category = "document"
    extensions = {".docx", ".doc"}


class TextParser(BaseParser):
    category = "text"
    extensions = {".txt", ".md", ".csv"}


class SpreadsheetParser(BaseParser):
    category = "spreadsheet"
    extensions = {".xlsx", ".xls"}


class PresentationParser(BaseParser):
    category = "presentation"
    extensions = {".pptx", ".ppt"}


class ImageParser(BaseParser):
    category = "image"
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


# ── Parser Registry ───────────────────────────────────────────────────────────

class ParserRegistry:
    _parsers: Dict[str, Type[BaseParser]] = {}

    @classmethod
    def register(cls, parser_cls: Type[BaseParser]) -> None:
        for ext in parser_cls.extensions:
            cls._parsers[ext.lower()] = parser_cls

    @classmethod
    def is_supported(cls, file_path: Path | str) -> bool:
        p = Path(file_path)
        return p.suffix.lower() in cls._parsers

    @classmethod
    def get_parser(cls, file_path: Path | str) -> Optional[Type[BaseParser]]:
        p = Path(file_path)
        return cls._parsers.get(p.suffix.lower())

    @classmethod
    def get_category(cls, file_path: Path | str) -> str:
        parser = cls.get_parser(file_path)
        return parser.category if parser else "unsupported"

    @classmethod
    def get_supported_extensions(cls) -> Set[str]:
        return set(cls._parsers.keys())


# Register default parsers
for p in [
    PDFParser,
    DOCXParser,
    TextParser,
    SpreadsheetParser,
    PresentationParser,
    ImageParser,
]:
    ParserRegistry.register(p)


def should_ignore_file(file_path: Path | str) -> bool:
    """
    Checks if a file or path should be ignored (temporary, system, dev folders).
    """
    path = Path(file_path)
    name = path.name.lower()

    # Ignore files starting with ~$ (Office temporary lock files)
    if name.startswith("~$") or name.startswith("."):
        return True

    if name in EXCLUDED_FILENAMES:
        return True

    if path.suffix.lower() in EXCLUDED_EXTENSIONS:
        return True

    # Check if any parent directory is blacklisted
    for part in path.parts[:-1]:
        if part.lower() in EXCLUDED_DIR_NAMES:
            return True

    return False


# Max file size: 15 MB to prevent memory exhaustion on cloud servers
MAX_SYNC_FILE_SIZE_BYTES = 15 * 1024 * 1024


def is_sync_candidate(file_path: Path | str) -> bool:
    """Returns True if the file is an active, readable, supported file within size limit."""
    path = Path(file_path)
    if not path.is_file():
        return False
    if should_ignore_file(path):
        return False
    try:
        if path.stat().st_size > MAX_SYNC_FILE_SIZE_BYTES:
            return False
    except Exception:
        return False
    return ParserRegistry.is_supported(path)
