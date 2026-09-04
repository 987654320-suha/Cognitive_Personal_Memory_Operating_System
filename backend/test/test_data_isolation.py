# LOCATION: backend/test/test_data_isolation.py
import io
import time
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_user_data_isolation_flow():
    # 1. Create User A
    user_a_email = f"user_a_{int(time.time())}@cognisphere.ai"
    res_a = client.post("/auth/register", json={"email": user_a_email, "password": "Password123!"})
    assert res_a.status_code == 201
    token_a = res_a.json()["token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Create User B
    user_b_email = f"user_b_{int(time.time())}@cognisphere.ai"
    res_b = client.post("/auth/register", json={"email": user_b_email, "password": "Password123!"})
    assert res_b.status_code == 201
    token_b = res_b.json()["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User A creates a private memory
    mem_payload = {
        "title": "User A Private Confidential Document",
        "description": "Secret cognitive information belonging exclusively to User A.",
        "importance_score": 0.9,
    }
    mem_res = client.post("/memories/", json=mem_payload, headers=headers_a)
    assert mem_res.status_code == 200
    user_a_mem_id = mem_res.json()["memory"]["id"]

    # 4. User A creates a private goal
    goal_payload = {
        "name": f"User A Secret Objective {int(time.time())}",
        "description": "User A private goal description",
    }
    goal_res = client.post("/goals/", json=goal_payload, headers=headers_a)
    assert goal_res.status_code == 200
    user_a_goal_id = goal_res.json()["id"]

    # 5. User B lists memories -> Must NOT contain User A's memory
    b_memories_res = client.get("/memories/", headers=headers_b)
    assert b_memories_res.status_code == 200
    b_mem_ids = [m["id"] for m in b_memories_res.json()]
    assert user_a_mem_id not in b_mem_ids

    # 6. User B attempts to get User A's memory detail -> Must return 404
    b_detail_res = client.get(f"/memories/{user_a_mem_id}", headers=headers_b)
    assert b_detail_res.status_code == 404

    # 7. User B attempts to delete User A's memory -> Must return 404
    b_del_res = client.delete(f"/memories/{user_a_mem_id}", headers=headers_b)
    assert b_del_res.status_code == 404

    # 8. User B lists goals -> Must NOT contain User A's goal
    b_goals_res = client.get("/goals/", headers=headers_b)
    assert b_goals_res.status_code == 200
    b_goal_ids = [g["id"] for g in b_goals_res.json()]
    assert user_a_goal_id not in b_goal_ids

    # 9. User B attempts to delete User A's goal -> Must return 404
    b_del_goal_res = client.delete(f"/goals/{user_a_goal_id}", headers=headers_b)
    assert b_del_goal_res.status_code == 404

    # 10. User A starts an upload job
    content = b"Secret upload content for User A isolation test."
    file_payload = {"file": ("user_a_secret.txt", io.BytesIO(content), "text/plain")}
    upload_res = client.post("/upload/", files=file_payload, headers=headers_a)
    assert upload_res.status_code == 202
    job_id_a = upload_res.json()["job_id"]

    # 11. User B attempts to check User A's job status -> Must return 404
    b_job_res = client.get(f"/upload/status/{job_id_a}", headers=headers_b)
    assert b_job_res.status_code == 404
    b_root_job_res = client.get(f"/status/{job_id_a}", headers=headers_b)
    assert b_root_job_res.status_code == 404

    # 12. User A checks their own job status -> Must return 200
    a_job_res = client.get(f"/upload/status/{job_id_a}", headers=headers_a)
    assert a_job_res.status_code == 200
    assert a_job_res.json()["job_id"] == job_id_a
