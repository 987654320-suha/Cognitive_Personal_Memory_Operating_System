"""
app/services/folder_watcher.py
===============================
Watches Desktop, Downloads, Documents, Pictures for new files.
On detection, runs the full CogniSphere memory pipeline.
Uses watchdog. Run as background thread from main.py or standalone.
"""

from __future__ import annotations
import os
import time
import threading
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("[FolderWatcher] watchdog not installed. Run: pip install watchdog")

from ai.memory_pipeline import run_pipeline


WATCHED_DIRS = [
    Path.home() / "Desktop",
    Path.home() / "Downloads",
    Path.home() / "Documents",
    Path.home() / "Pictures",
]

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp",
    ".pdf", ".docx", ".doc", ".txt",
}


class CogniSphereEventHandler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    def __init__(self):
        self._processing: set[str] = set()
        self._lock = threading.Lock()

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return
        # Debounce: avoid double-processing
        with self._lock:
            if str(path) in self._processing:
                return
            self._processing.add(str(path))

        # Small delay to ensure file is fully written
        time.sleep(1.5)
        try:
            print(f"[FolderWatcher] New file detected: {path.name}")
            result = run_pipeline(str(path))
            print(f"[FolderWatcher] Ingested: {result.get('title')} (goals: {result.get('detected_goals', [])})")
            
            # âœ… Refresh cache and rebuild indices after successful ingestion
            _refresh_after_change()
            
        except Exception as e:
            print(f"[FolderWatcher] Pipeline error for {path.name}: {e}")
        finally:
            with self._lock:
                self._processing.discard(str(path))


def start_watcher():
    if not WATCHDOG_AVAILABLE:
        print("[FolderWatcher] Cannot start â€” watchdog not installed.")
        return None

    handler = CogniSphereEventHandler()
    observer = Observer()

    watched = 0
    for watch_dir in WATCHED_DIRS:
        if watch_dir.exists():
            observer.schedule(handler, str(watch_dir), recursive=True)
            watched += 1
            print(f"[FolderWatcher] Watching: {watch_dir}")

    if watched == 0:
        print("[FolderWatcher] No valid directories to watch.")
        return None

    observer.start()
    print(f"[FolderWatcher] Started â€” watching {watched} directories.")
    return observer


def start_watcher_thread():
    """Start watcher in a background daemon thread."""
    t = threading.Thread(target=_run_watcher, daemon=True)
    t.start()
    return t


def _run_watcher():
    observer = start_watcher()
    if observer:
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


def _refresh_after_change():
    """
    Refresh memory cache and rebuild search indices after any data modification.
    Called after successful pipeline ingestion.
    """
    try:
        from app.services.database_service import refresh_memory_cache, get_all_memories
        from ai.faiss_service import build_index
        from ai.hybrid_search import build_bm25
        
        # Refresh in-memory cache
        refresh_memory_cache()
        print("[FolderWatcher] Memory cache refreshed after ingestion")
        
        # Rebuild FAISS and BM25 indices
        memories = get_all_memories()
        if memories:
            build_index(memories)
            print(f"[FolderWatcher] FAISS index rebuilt with {len(memories)} memories")
            
            build_bm25(memories)
            print(f"[FolderWatcher] BM25 index rebuilt with {len(memories)} memories")
        else:
            print("[FolderWatcher] No memories to index")
    except Exception as e:
        print(f"[FolderWatcher] Error refreshing after change: {e}")


if __name__ == "__main__":
    observer = start_watcher()
    if observer:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


