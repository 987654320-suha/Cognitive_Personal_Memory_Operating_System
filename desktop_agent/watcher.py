# LOCATION: desktop_agent/watcher.py
"""
watcher.py
==========
Real-time filesystem observer for CogniSphere Desktop Agent using watchdog.
Debounces file modification events and enqueues sync jobs without blocking the OS.
"""

from __future__ import annotations
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Set

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object

from desktop_agent.parsers import is_sync_candidate, should_ignore_file
from desktop_agent.scanner import compute_sha256
from desktop_agent.sync_queue import SyncQueue


class DesktopFileEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        folder_root: Path,
        folder_name: str,
        queue: SyncQueue,
        debounce_seconds: float = 1.5,
    ):
        super().__init__()
        self.folder_root = folder_root
        self.folder_name = folder_name
        self.queue = queue
        self.debounce_seconds = debounce_seconds
        self._pending_timers: Dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def _get_relative_path(self, file_path: Path) -> str:
        try:
            rel = file_path.relative_to(self.folder_root).as_posix()
            return f"{self.folder_name}/{rel}"
        except Exception:
            return f"{self.folder_name}/{file_path.name}"

    def on_created(self, event):
        if event.is_directory:
            return
        self._schedule_process(Path(event.src_path), "SYNC")

    def on_modified(self, event):
        if event.is_directory:
            return
        self._schedule_process(Path(event.src_path), "SYNC")

    def on_deleted(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if should_ignore_file(path):
            return

        rel_path = self._get_relative_path(path)
        print(f"[Watcher] File deleted locally: {path.name}")
        self.queue.enqueue("DELETE", {"relative_path": rel_path})

    def on_moved(self, event):
        if event.is_directory:
            return
        # Old path deleted
        old_path = Path(event.src_path)
        if not should_ignore_file(old_path):
            self.queue.enqueue("DELETE", {"relative_path": self._get_relative_path(old_path)})

        # New path synced
        new_path = Path(event.dest_path)
        if is_sync_candidate(new_path):
            self._schedule_process(new_path, "SYNC")

    def _schedule_process(self, path: Path, job_type: str) -> None:
        path_str = str(path.resolve())
        with self._lock:
            if path_str in self._pending_timers:
                self._pending_timers[path_str].cancel()

            t = threading.Timer(
                self.debounce_seconds,
                self._handle_debounced_event,
                args=[path, job_type],
            )
            self._pending_timers[path_str] = t
            t.start()

    def _handle_debounced_event(self, path: Path, job_type: str) -> None:
        path_str = str(path.resolve())
        with self._lock:
            self._pending_timers.pop(path_str, None)

        if not path.exists() or not is_sync_candidate(path):
            return

        sha256 = compute_sha256(path)
        if not sha256:
            return

        try:
            stat = path.stat()
            mtime = stat.st_mtime
            rel_path = self._get_relative_path(path)
        except Exception:
            return

        print(f"[Watcher] Detected ready file: {path.name}")
        self.queue.enqueue("SYNC", {
            "abs_path": path_str,
            "relative_path": rel_path,
            "filename": path.name,
            "sha256": sha256,
            "mtime": mtime,
        })


class WatcherManager:
    """Manages active watchdog observers across authorized folders."""
    def __init__(self, queue: SyncQueue):
        self.queue = queue
        self.observer: Optional[Observer] = None
        self.active_watches: Dict[str, Any] = {}
        self._running = False

    def start(self, folders: list[dict]) -> bool:
        if not WATCHDOG_AVAILABLE:
            print("[Watcher] watchdog package not available.")
            return False

        if self._running:
            self.stop()

        self.observer = Observer()
        watched_count = 0

        for f in folders:
            if not f.get("enabled"):
                continue
            path = Path(f["path"]).resolve()
            if path.exists() and path.is_dir():
                handler = DesktopFileEventHandler(
                    folder_root=path,
                    folder_name=f["name"],
                    queue=self.queue,
                )
                watch = self.observer.schedule(handler, str(path), recursive=True)
                self.active_watches[str(path)] = watch
                watched_count += 1
                print(f"[Watcher] Monitoring folder: {f['name']} ({path})")

        if watched_count > 0:
            self.observer.start()
            self._running = True
            print(f"[Watcher] Started live monitoring on {watched_count} folders.")
            return True
        return False

    def stop(self) -> None:
        if self.observer and self._running:
            try:
                self.observer.stop()
                self.observer.join(timeout=2)
            except Exception:
                pass
        self._running = False
        self.active_watches.clear()
        print("[Watcher] Live monitoring stopped.")

    def is_alive(self) -> bool:
        return self._running and self.observer is not None and self.observer.is_alive()
