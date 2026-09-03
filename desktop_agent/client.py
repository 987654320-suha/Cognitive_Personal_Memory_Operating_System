# LOCATION: desktop_agent/client.py
"""
client.py
=========
HTTP client for CogniSphere Desktop Agent.
Handles backend health checks, device pairing, heartbeats, and multipart file sync.
"""

from __future__ import annotations
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import requests

from desktop_agent.config import AgentConfig


class BackendClient:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"CogniSphere-DesktopAgent/2.0 ({config.os_info})",
        })

    @property
    def base_url(self) -> str:
        return self.config.server_url.rstrip("/")

    def check_health(self) -> bool:
        """Verifies backend connectivity via /health."""
        try:
            url = f"{self.base_url}/health"
            res = self.session.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                return data.get("status") == "healthy" or "status" in data
            return False
        except Exception:
            return False

    def pair_device(self, device_name: str, os_info: str) -> Optional[Dict[str, Any]]:
        """Pairs with backend /sync/pair and retrieves device_id and auth_token."""
        try:
            url = f"{self.base_url}/sync/pair"
            payload = {"device_name": device_name, "os_info": os_info}
            res = self.session.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                return res.json()
            print(f"[Client] Pairing failed ({res.status_code}): {res.text}")
            return None
        except Exception as e:
            print(f"[Client] Pairing error: {e}")
            return None

    def send_heartbeat(self, status: str, folders: List[Dict[str, Any]]) -> bool:
        """Sends periodic heartbeat to /sync/heartbeat."""
        if not self.config.is_paired():
            return False
        try:
            url = f"{self.base_url}/sync/heartbeat"
            payload = {
                "device_id": self.config.device_id,
                "auth_token": self.config.auth_token,
                "status": status,
                "watched_folders": folders,
            }
            res = self.session.post(url, json=payload, timeout=8)
            return res.status_code == 200
        except Exception as e:
            return False

    def sync_file(
        self,
        file_path: Path | str,
        relative_path: str,
        sha256_hash: str,
        modified_at: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Uploads file to /sync/file with metadata.
        Returns response dict or None on failure.
        """
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return None

        try:
            url = f"{self.base_url}/sync/file"
            data = {
                "device_id":     self.config.device_id,
                "auth_token":    self.config.auth_token,
                "relative_path": relative_path,
                "sha256_hash":   sha256_hash,
                "modified_at":   modified_at,
            }
            with open(p, "rb") as f:
                files = {"file": (p.name, f, "application/octet-stream")}
                res = self.session.post(url, data=data, files=files, timeout=60)

            if res.status_code == 200:
                return res.json()
            else:
                print(f"[Client] Sync failed for {p.name} ({res.status_code}): {res.text}")
                return None
        except Exception as e:
            print(f"[Client] Network error syncing {p.name}: {e}")
            return None

    def delete_file(self, relative_path: str) -> bool:
        """Notifies deletion to /sync/file."""
        if not self.config.is_paired():
            return False
        try:
            url = f"{self.base_url}/sync/file"
            payload = {
                "device_id":     self.config.device_id,
                "auth_token":    self.config.auth_token,
                "relative_path": relative_path,
            }
            res = self.session.request("DELETE", url, json=payload, timeout=10)
            return res.status_code == 200
        except Exception as e:
            print(f"[Client] Error sending delete for {relative_path}: {e}")
            return False
