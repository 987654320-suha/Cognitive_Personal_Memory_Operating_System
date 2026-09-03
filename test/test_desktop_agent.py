"""
test_desktop_agent.py
=====================
Unit tests for CogniSphere Desktop Agent modules.
Tests:
- Folder discovery and configuration management
- Extensible parser registry & temporary file blacklisting
- SHA-256 hash calculation and manifest tracking
- Incremental change detection (added, modified, deleted)
- Local persistent offline sync queue
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from desktop_agent.config import AgentConfig, get_default_windows_folders
from desktop_agent.parsers import (
    ParserRegistry,
    should_ignore_file,
    is_sync_candidate,
    PDFParser,
    TextParser,
    ImageParser,
)
from desktop_agent.scanner import compute_sha256, LocalManifest, FolderScanner
from desktop_agent.sync_queue import SyncQueue


def test_windows_folders_discovery():
    folders = get_default_windows_folders()
    assert isinstance(folders, list)
    # Folders must NOT be enabled by default (permission required)
    for f in folders:
        assert f["enabled"] is False
        assert "path" in f
        assert "name" in f


def test_parser_registry():
    assert ParserRegistry.is_supported("document.pdf")
    assert ParserRegistry.is_supported("notes.txt")
    assert ParserRegistry.is_supported("report.docx")
    assert ParserRegistry.is_supported("photo.png")
    assert ParserRegistry.is_supported("table.csv")
    assert ParserRegistry.is_supported("slides.pptx")
    assert not ParserRegistry.is_supported("program.exe")
    assert not ParserRegistry.is_supported("archive.zip")

    assert ParserRegistry.get_category("document.pdf") == "document"
    assert ParserRegistry.get_category("photo.jpg") == "image"
    assert ParserRegistry.get_category("notes.txt") == "text"


def test_ignore_rules():
    # Office temp lock files
    assert should_ignore_file("~$resume.docx")
    # Hidden files
    assert should_ignore_file(".git")
    assert should_ignore_file(".DS_Store")
    assert should_ignore_file("desktop.ini")
    assert should_ignore_file("thumbs.db")
    # Temporary extensions
    assert should_ignore_file("download.crdownload")
    assert should_ignore_file("file.tmp")
    # Valid candidate
    assert not should_ignore_file("my_resume.pdf")


def test_manifest_and_sha256(tmp_path):
    test_file = tmp_path / "hello.txt"
    test_file.write_text("Hello CogniSphere!", encoding="utf-8")

    sha = compute_sha256(test_file)
    assert len(sha) == 64  # Valid SHA-256 hex string

    manifest_path = tmp_path / "manifest.json"
    manifest = LocalManifest(manifest_path)
    manifest.set(str(test_file), {"sha256": sha, "mtime": 100})

    loaded = LocalManifest(manifest_path)
    entry = loaded.get(str(test_file))
    assert entry is not None
    assert entry["sha256"] == sha


def test_incremental_folder_scanner(tmp_path):
    manifest_path = tmp_path / "test_manifest.json"
    manifest = LocalManifest(manifest_path)
    scanner = FolderScanner(manifest)

    # 1. Create files in temp folder
    watch_folder = tmp_path / "Documents"
    watch_folder.mkdir()

    f1 = watch_folder / "note1.txt"
    f1.write_text("First note", encoding="utf-8")
    f2 = watch_folder / "note2.md"
    f2.write_text("Second note", encoding="utf-8")

    # Initial scan: should detect 2 added files
    res1 = scanner.scan_folder(str(watch_folder), "Documents")
    assert len(res1["added"]) == 2
    assert len(res1["modified"]) == 0
    assert len(res1["deleted"]) == 0

    # Simulate agent recording them in manifest
    for item in res1["added"]:
        manifest.set(item["abs_path"], {
            "relative_path": item["relative_path"],
            "sha256": item["sha256"],
            "mtime": item["mtime"],
            "size": item["size"],
        })

    # Second scan with no changes: unchanged_count == 2
    res2 = scanner.scan_folder(str(watch_folder), "Documents")
    assert len(res2["added"]) == 0
    assert len(res2["modified"]) == 0
    assert res2["unchanged_count"] == 2

    # 2. Modify f1
    f1.write_text("First note UPDATED", encoding="utf-8")
    res3 = scanner.scan_folder(str(watch_folder), "Documents")
    assert len(res3["modified"]) == 1
    assert res3["modified"][0]["filename"] == "note1.txt"

    # 3. Delete f2
    f2.unlink()
    res4 = scanner.scan_folder(str(watch_folder), "Documents")
    assert len(res4["deleted"]) == 1
    assert res4["deleted"][0]["filename"] == "note2.md"


def test_sync_queue(tmp_path):
    queue_db = tmp_path / "test_queue.db"
    q = SyncQueue(queue_db)

    job_id = q.enqueue("SYNC", {"relative_path": "Docs/a.pdf", "sha256": "abc"})
    assert job_id > 0
    assert q.count_pending() == 1

    pending = q.get_pending()
    assert len(pending) == 1
    assert pending[0]["job_type"] == "SYNC"
    assert pending[0]["payload"]["relative_path"] == "Docs/a.pdf"

    q.mark_done(job_id)
    assert q.count_pending() == 0
