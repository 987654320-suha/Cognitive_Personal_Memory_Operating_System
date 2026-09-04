"""
test_sync_service.py
====================
Unit and integration tests for CogniSphere Desktop Agent sync endpoints.
Tests:
- Device pairing and authentication
- File synchronization with SHA-256 deduplication
- Deduplication reuse of existing memory
- File deletion and memory cleanup
- Status overview reporting
"""

import io
import time
import hashlib
import pytest
from fastapi.testclient import TestClient

import main
from database.database import SessionLocal, Base, engine
from app.models.sync_device import SyncDevice
from app.models.indexed_file import IndexedFile
from app.models.memory import Memory

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


def test_device_pairing():
    res = client.post("/sync/pair", json={
        "device_name": "Test Windows PC",
        "os_info": "Windows 11",
    })
    assert res.status_code == 200
    data = res.json()
    assert "device_id" in data
    assert "auth_token" in data
    assert data["device_name"] == "Test Windows PC"
    assert data["auth_token"].startswith("cs_")


def test_heartbeat_unauthorized():
    res = client.post("/sync/heartbeat", json={
        "device_id": "non-existent-device",
        "auth_token": "invalid-token",
        "status": "watching",
    })
    assert res.status_code == 401


def test_heartbeat_authorized():
    pair_res = client.post("/sync/pair", json={"device_name": "Laptop", "os_info": "Windows 10"}).json()
    device_id = pair_res["device_id"]
    auth_token = pair_res["auth_token"]

    res = client.post("/sync/heartbeat", json={
        "device_id": device_id,
        "auth_token": auth_token,
        "status": "watching",
        "watched_folders": [{"id": "docs", "name": "Documents", "enabled": True, "file_count": 42}],
    })
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_file_sync_and_deduplication():
    # 1. Pair a test device
    pair_res = client.post("/sync/pair", json={"device_name": "Desktop PC", "os_info": "Windows 11"}).json()
    device_id = pair_res["device_id"]
    auth_token = pair_res["auth_token"]

    # Sample file content with unique run token
    content = f"Cognitive Personal Memory Operating System sync test notes {time.time()}.".encode()
    file_hash = hashlib.sha256(content).hexdigest()

    # 2. Sync first file
    res1 = client.post(
        "/sync/file",
        data={
            "device_id": device_id,
            "auth_token": auth_token,
            "relative_path": "Documents/notes.txt",
            "sha256_hash": file_hash,
            "modified_at": "2026-09-03T12:00:00Z",
        },
        files={"file": ("notes.txt", io.BytesIO(content), "text/plain")},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["success"] is True
    assert data1["deduplicated"] is False
    memory_id1 = data1["memory_id"]
    assert memory_id1 is not None

    # 3. Sync identical file from different path (e.g. copied to Downloads)
    res2 = client.post(
        "/sync/file",
        data={
            "device_id": device_id,
            "auth_token": auth_token,
            "relative_path": "Downloads/notes-copy.txt",
            "sha256_hash": file_hash,
            "modified_at": "2026-09-03T12:05:00Z",
        },
        files={"file": ("notes-copy.txt", io.BytesIO(content), "text/plain")},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["success"] is True
    # MUST be deduplicated and reuse original memory ID!
    assert data2["deduplicated"] is True
    assert data2["memory_id"] == memory_id1

    # 4. Check sync status
    status_res = client.get("/sync/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["total_devices"] >= 1
    assert status_data["total_indexed_files"] >= 2


def test_file_deletion():
    pair_res = client.post("/sync/pair", json={"device_name": "PC", "os_info": "Windows"}).json()
    device_id = pair_res["device_id"]
    auth_token = pair_res["auth_token"]

    content = b"Temporary note to be deleted soon."
    file_hash = hashlib.sha256(content).hexdigest()

    client.post(
        "/sync/file",
        data={
            "device_id": device_id,
            "auth_token": auth_token,
            "relative_path": "Desktop/temp_note.txt",
            "sha256_hash": file_hash,
        },
        files={"file": ("temp_note.txt", io.BytesIO(content), "text/plain")},
    )

    del_res = client.request(
        "DELETE",
        "/sync/file",
        json={
            "device_id": device_id,
            "auth_token": auth_token,
            "relative_path": "Desktop/temp_note.txt",
        },
    )
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True
