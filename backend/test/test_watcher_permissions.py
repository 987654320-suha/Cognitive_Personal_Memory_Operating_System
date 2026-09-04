# LOCATION: backend/test/test_watcher_permissions.py
import time
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_watcher_permissions_and_isolation():
    # 1. Register User A
    user_a_email = f"watcher_user_a_{int(time.time())}@cognisphere.ai"
    res_a = client.post("/auth/register", json={"email": user_a_email, "password": "Password123!"})
    assert res_a.status_code == 201
    token_a = res_a.json()["token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B
    user_b_email = f"watcher_user_b_{int(time.time())}@cognisphere.ai"
    res_b = client.post("/auth/register", json={"email": user_b_email, "password": "Password123!"})
    assert res_b.status_code == 201
    token_b = res_b.json()["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Unauthenticated request to /watcher/locations fails with 401
    unauth_res = client.get("/watcher/locations")
    assert unauth_res.status_code == 401

    # 4. User A lists locations -> Auto-seeds standard folders (Documents, Downloads, Pictures, Desktop)
    locs_a = client.get("/watcher/locations", headers=headers_a)
    assert locs_a.status_code == 200
    a_items = locs_a.json()
    assert len(a_items) >= 4
    names_a = [item["display_name"] for item in a_items]
    assert "Documents" in names_a
    assert "Downloads" in names_a
    assert "Pictures" in names_a
    assert "Desktop" in names_a

    # 5. User A adds a custom watch location
    custom_loc = {
        "path": "E:/UserA_Projects/ResearchDocs",
        "display_name": "User A Research Docs",
        "location_type": "custom",
        "permission_status": "granted",
        "enabled": True,
    }
    create_res = client.post("/watcher/locations", json=custom_loc, headers=headers_a)
    assert create_res.status_code == 201
    user_a_loc_id = create_res.json()["id"]
    assert create_res.json()["display_name"] == "User A Research Docs"

    # 6. User A pauses the location
    pause_res = client.post(f"/watcher/locations/{user_a_loc_id}/pause", headers=headers_a)
    assert pause_res.status_code == 200
    assert pause_res.json()["enabled"] is False

    # 7. User A resumes the location
    resume_res = client.post(f"/watcher/locations/{user_a_loc_id}/resume", headers=headers_a)
    assert resume_res.status_code == 200
    assert resume_res.json()["enabled"] is True

    # 8. User B lists locations -> Must NOT contain User A's custom location
    locs_b = client.get("/watcher/locations", headers=headers_b)
    assert locs_b.status_code == 200
    b_items = locs_b.json()
    b_ids = [item["id"] for item in b_items]
    assert user_a_loc_id not in b_ids

    # 9. User B attempts to modify User A's location -> 404
    b_mod_res = client.patch(
        f"/watcher/locations/{user_a_loc_id}",
        json={"display_name": "Hacked Name"},
        headers=headers_b,
    )
    assert b_mod_res.status_code == 404

    # 10. User B attempts to delete User A's location -> 404
    b_del_res = client.delete(f"/watcher/locations/{user_a_loc_id}", headers=headers_b)
    assert b_del_res.status_code == 404

    # 11. User A deletes their location -> 200
    a_del_res = client.delete(f"/watcher/locations/{user_a_loc_id}", headers=headers_a)
    assert a_del_res.status_code == 200
    assert a_del_res.json()["status"] == "ok"
