# LOCATION: desktop_agent/config.py
"""
config.py
=========
Configuration and folder permission manager for CogniSphere Desktop Agent.
Resolves Windows user directories safely and persists configuration locally.
"""

from __future__ import annotations
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


def get_agent_data_dir() -> Path:
    """Returns directory for storing agent configuration and local manifest."""
    base = Path.home() / ".cognisphere"
    base.mkdir(parents=True, exist_ok=True)
    return base


CONFIG_FILE = get_agent_data_dir() / "agent_config.json"


def get_default_windows_folders() -> List[Dict[str, Any]]:
    """
    Safely resolves standard Windows user folders without hardcoded usernames.
    """
    home = Path.home()
    candidates = [
        {"id": "documents", "name": "Documents", "path": str(home / "Documents")},
        {"id": "desktop",   "name": "Desktop",   "path": str(home / "Desktop")},
        {"id": "downloads", "name": "Downloads", "path": str(home / "Downloads")},
        {"id": "pictures",  "name": "Pictures",  "path": str(home / "Pictures")},
        {"id": "videos",    "name": "Videos",    "path": str(home / "Videos")},
    ]

    folders = []
    for c in candidates:
        p = Path(c["path"])
        if p.exists() and p.is_dir():
            folders.append({
                "id":         c["id"],
                "name":       c["name"],
                "path":       str(p),
                "enabled":    False,  # Explicit user permission required
                "status":     "idle",
                "file_count": 0,
            })
    return folders


class AgentConfig:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_FILE
        self.server_url: str = "https://cognisphere-backend-ya2y.onrender.com"
        self.device_id: str = ""
        self.auth_token: str = ""
        self.device_name: str = f"Windows PC ({os.environ.get('COMPUTERNAME', 'Desktop')})"
        self.os_info: str = f"Windows {sys.getwindowsversion().major}" if sys.platform == "win32" else sys.platform
        self.watched_folders: List[Dict[str, Any]] = []
        self.scan_interval: int = 60
        self.heartbeat_interval: int = 15
        self.is_paused: bool = False
        self.load()

    def load(self) -> None:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.server_url = data.get("server_url", self.server_url)
                self.device_id = data.get("device_id", "")
                self.auth_token = data.get("auth_token", "")
                self.device_name = data.get("device_name", self.device_name)
                self.os_info = data.get("os_info", self.os_info)
                self.watched_folders = data.get("watched_folders", [])
                self.scan_interval = data.get("scan_interval", 60)
                self.heartbeat_interval = data.get("heartbeat_interval", 15)
                self.is_paused = data.get("is_paused", False)
            except Exception as e:
                print(f"[Config] Error loading config: {e}")

        # Initialize default folders if empty
        if not self.watched_folders:
            self.watched_folders = get_default_windows_folders()

    def save(self) -> None:
        data = {
            "server_url":         self.server_url.rstrip("/"),
            "device_id":          self.device_id,
            "auth_token":         self.auth_token,
            "device_name":        self.device_name,
            "os_info":            self.os_info,
            "watched_folders":    self.watched_folders,
            "scan_interval":      self.scan_interval,
            "heartbeat_interval": self.heartbeat_interval,
            "is_paused":          self.is_paused,
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def is_paired(self) -> bool:
        return bool(self.device_id and self.auth_token)

    def get_enabled_folders(self) -> List[Dict[str, Any]]:
        return [f for f in self.watched_folders if f.get("enabled") and Path(f["path"]).exists()]

    def add_custom_folder(self, folder_path: str, name: Optional[str] = None) -> bool:
        p = Path(folder_path).resolve()
        if not p.exists() or not p.is_dir():
            return False

        path_str = str(p)
        for f in self.watched_folders:
            if f["path"] == path_str:
                f["enabled"] = True
                self.save()
                return True

        self.watched_folders.append({
            "id":         f"custom_{len(self.watched_folders)+1}",
            "name":       name or p.name or "Custom Folder",
            "path":       path_str,
            "enabled":    True,
            "status":     "idle",
            "file_count": 0,
        })
        self.save()
        return True

    def toggle_folder(self, folder_id: str, enabled: bool) -> bool:
        for f in self.watched_folders:
            if f.get("id") == folder_id:
                f["enabled"] = enabled
                self.save()
                return True
        return False

    def remove_folder(self, folder_id: str) -> bool:
        initial_len = len(self.watched_folders)
        self.watched_folders = [f for f in self.watched_folders if f.get("id") != folder_id]
        if len(self.watched_folders) < initial_len:
            self.save()
            return True
        return False
