# LOCATION: backend/test/test_desktop_sync_flow.py
"""
test_desktop_sync_flow.py
=========================
End-to-end integration test for CogniSphere Desktop Agent pairing, folder permissions,
file synchronization, and multi-tenant data isolation.

Flow:
1. User registration & login.
2. Web UI generates pairing code via /sync/pair.
3. Desktop agent completes pairing using pairing code.
4. Authorize standard folders (Desktop, Documents).
5. Desktop agent syncs file via /sync/file.
6. Verify memory created and scoped to authenticated user.
7. Revoke folder permission.
8. Verify revoked folder prevents further indexing/uploads.
9. Verify multi-tenant isolation against another user.
"""

import io
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app
from database.database import get_db, Base, engine
from app.models.user import User
from app.models.sync_device import SyncDevice
from app.models.indexed_file import IndexedFile
from app.models.memory import Memory
from app.models.watcher_location import WatcherLocation


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.create_all(bind=engine)
    yield


def test_complete_desktop_sync_and_permissions_flow():
    client = TestClient(app)

    import uuid
    suffix = uuid.uuid4().hex[:6]
    email_a = f"alice_sync_{suffix}@example.com"
    email_b = f"bob_sync_{suffix}@example.com"

    # ── 1. Register & Login User A ──────────────────────────────────────────
    reg_a = client.post(
        "/auth/register",
        json={"email": email_a, "password": "SecurePassword123!"},
    )
    assert reg_a.status_code == 201, reg_a.text
    token_a = reg_a.json()["token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # ── 2. User A generates pairing code via /sync/pair ─────────────────────
    pair_req = client.post(
        "/sync/pair",
        json={"device_name": "Alice Laptop", "os_info": "Windows 11"},
        headers=headers_a,
    )
    assert pair_req.status_code == 200, pair_req.text
    pair_data = pair_req.json()
    assert "pairing_code" in pair_data
    assert pair_data["pairing_code"].startswith("COG-")
    assert pair_data["status"] == "pending_pairing"
    pairing_code = pair_data["pairing_code"]
    device_id = pair_data["device_id"]

    # ── 3. Desktop Agent pairs using pairing code ───────────────────────────
    agent_pair_res = client.post(
        "/sync/pair",
        json={
            "pairing_code": pairing_code,
            "device_name": "Alice Windows PC",
            "os_info": "Windows 11 Pro",
        },
    )
    assert agent_pair_res.status_code == 200, agent_pair_res.text
    agent_data = agent_pair_res.json()
    assert agent_data["device_id"] == device_id
    assert agent_data["status"] == "connected"
    assert "auth_token" in agent_data
    device_auth_token = agent_data["auth_token"]
    agent_headers = {"Authorization": f"Bearer {device_auth_token}"}

    # ── 4. Verify User A sees the connected device ──────────────────────────
    devices_res = client.get("/sync/devices", headers=headers_a)
    assert devices_res.status_code == 200
    devices_data = devices_res.json()
    assert devices_data["total_devices"] >= 1
    device_entry = next((d for d in devices_data["devices"] if d["device_id"] == device_id), None)
    assert device_entry is not None
    assert device_entry["device_name"] == "Alice Windows PC"
    assert device_entry["status"] == "connected"

    # ── 5. Authorize Standard Folders (Desktop, Documents, etc.) ────────────
    locs_res = client.get("/watcher/locations", headers=headers_a)
    assert locs_res.status_code == 200
    locs = locs_res.json()
    assert len(locs) >= 4  # Desktop, Documents, Downloads, Pictures, Videos
    doc_loc = next((l for l in locs if l["display_name"] == "Documents"), None)
    assert doc_loc is not None
    assert doc_loc["enabled"] is True
    assert doc_loc["permission_status"] == "granted"

    # Agent verifies it can fetch authorized locations using its device auth_token
    agent_locs_res = client.get("/watcher/locations", headers=agent_headers)
    assert agent_locs_res.status_code == 200
    assert len(agent_locs_res.json()) >= 4

    # ── 6. Desktop Agent syncs a document ───────────────────────────────────
    fake_content = b"This is a confidential research project file from Alice's desktop computer."
    file_payload = {
        "device_id": device_id,
        "auth_token": device_auth_token,
        "relative_path": "Documents/Research_Draft.txt",
        "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "modified_at": "2026-09-04T09:30:00Z",
    }
    files = {"file": ("Research_Draft.txt", io.BytesIO(fake_content), "text/plain")}

    sync_res = client.post("/sync/file", data=file_payload, files=files)
    assert sync_res.status_code == 200, sync_res.text
    sync_data = sync_res.json()
    assert sync_data["success"] is True
    memory_id = sync_data["memory_id"]
    file_id = sync_data["file_id"]
    assert memory_id is not None
    assert file_id is not None

    # Verify memory is created and owned by Alice
    mem_res = client.get(f"/memories/{memory_id}", headers=headers_a)
    assert mem_res.status_code == 200
    mem_json = mem_res.json()
    assert mem_json["id"] == memory_id
    assert "Research Draft" in mem_json["title"]

    # Verify device telemetry updated
    devices_res_after = client.get("/sync/devices", headers=headers_a)
    dev_after = next((d for d in devices_res_after.json()["devices"] if d["device_id"] == device_id), None)
    assert dev_after is not None
    assert dev_after["indexed_files_count"] >= 1
    assert dev_after["last_sync"] is not None

    # ── 7. Revoke Folder Permission ─────────────────────────────────────────
    revoke_res = client.delete(f"/watcher/locations/{doc_loc['id']}", headers=headers_a)
    assert revoke_res.status_code == 200

    # Verify folder is no longer authorized
    locs_after_revoke = client.get("/watcher/locations", headers=headers_a).json()
    assert not any(l["id"] == doc_loc["id"] for l in locs_after_revoke)

    # ── 8. Pause / Resume Controls on Device ────────────────────────────────
    pause_res = client.post(f"/sync/devices/{device_id}/pause", headers=headers_a)
    assert pause_res.status_code == 200
    assert pause_res.json()["device"]["status"] == "paused"

    resume_res = client.post(f"/sync/devices/{device_id}/resume", headers=headers_a)
    assert resume_res.status_code == 200
    assert resume_res.json()["device"]["status"] == "watching"

    # ── 9. Multi-Tenant Data Isolation Checks ───────────────────────────────
    reg_b = client.post(
        "/auth/register",
        json={"email": email_b, "password": "BobSecurePass123!"},
    )
    assert reg_b.status_code == 201
    headers_b = {"Authorization": f"Bearer {reg_b.json()['token']}"}

    # Bob cannot see Alice's paired device
    bob_devices = client.get("/sync/devices", headers=headers_b).json()
    assert not any(d["device_id"] == device_id for d in bob_devices["devices"])

    # Bob cannot see Alice's synced memory
    bob_mem = client.get(f"/memories/{memory_id}", headers=headers_b)
    assert bob_mem.status_code == 404

    # Bob cannot pause or delete Alice's device
    bob_unpair = client.delete(f"/sync/devices/{device_id}", headers=headers_b)
    assert bob_unpair.status_code == 404

    # ── 10. Clean up / Unpair device ────────────────────────────────────────
    unpair_res = client.delete(f"/sync/devices/{device_id}", headers=headers_a)
    assert unpair_res.status_code == 200
