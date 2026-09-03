# ðŸ“ LOCATION: backend/app/routes/watcher_routes.py
"""
watcher_routes.py
=================
API endpoints to control the folder watcher at runtime.
Start, stop, and check watcher status without restarting the server.
"""

from fastapi import APIRouter
from pathlib import Path

router = APIRouter(prefix="/watcher", tags=["watcher"])

_observer = None   # global watcher instance


@router.get("/status")
def watcher_status():
    """Returns whether the folder watcher is currently running."""
    global _observer
    is_running = _observer is not None and _observer.is_alive()

    watched_dirs = [
        str(d) for d in [
            Path.home() / "Desktop",
            Path.home() / "Downloads",
            Path.home() / "Documents",
            Path.home() / "Pictures",
        ] if d.exists()
    ]

    return {
        "running":      is_running,
        "watched_dirs": watched_dirs,
    }


@router.post("/start")
def start_watcher():
    """Starts the folder watcher if not already running."""
    global _observer
    if _observer is not None and _observer.is_alive():
        return {"message": "Watcher already running"}

    try:
        from app.services.folder_watcher import start_watcher as _start
        _observer = _start()
        if _observer:
            return {"message": "Watcher started successfully"}
        return {"message": "No valid directories to watch", "started": False}
    except Exception as e:
        return {"error": str(e), "started": False}


@router.post("/stop")
def stop_watcher():
    """Stops the folder watcher."""
    global _observer
    if _observer is None or not _observer.is_alive():
        return {"message": "Watcher is not running"}
    try:
        _observer.stop()
        _observer.join()
        _observer = None
        return {"message": "Watcher stopped"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/restart")
def restart_watcher():
    """Stops and restarts the folder watcher."""
    stop_watcher()
    return start_watcher()


