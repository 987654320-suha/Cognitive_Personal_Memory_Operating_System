# LOCATION: backend/test/test_upload_routes.py
import io
import time
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_upload_status():
    res = client.get("/upload/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "embedding_model" in data
    assert ".pdf" in data["supported_extensions"]


def test_upload_returns_202_immediately():
    content = b"Async upload test document for CogniSphere background task processing."
    file_payload = {"file": ("async_test.txt", io.BytesIO(content), "text/plain")}
    
    t0 = time.time()
    res = client.post("/upload/", files=file_payload)
    elapsed = time.time() - t0

    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "processing"
    assert "job_id" in data
    assert data["filename"] == "async_test.txt"


def test_poll_job_status_until_completed():
    content = b"Machine learning and vector embeddings with FAISS and BM25 hybrid search."
    file_payload = {"file": ("job_poll_test.txt", io.BytesIO(content), "text/plain")}
    
    upload_res = client.post("/upload/", files=file_payload)
    assert upload_res.status_code == 202
    job_id = upload_res.json()["job_id"]

    # Poll /upload/status/{job_id}
    completed = False
    for _ in range(30):
        res = client.get(f"/upload/status/{job_id}")
        assert res.status_code == 200
        job_data = res.json()
        assert job_data["job_id"] == job_id
        if job_data["status"] == "completed":
            completed = True
            assert job_data["memory_id"] is not None
            assert job_data["memory"]["id"] == job_data["memory_id"]
            break
        elif job_data["status"] == "failed":
            pytest.fail(f"Job failed unexpectedly: {job_data.get('error')}")
        time.sleep(0.5)

    assert completed, f"Job {job_id} did not complete within 15 seconds"


def test_job_status_root_alias():
    content = b"Testing root /status/{job_id} endpoint alias."
    file_payload = {"file": ("alias_test.txt", io.BytesIO(content), "text/plain")}
    
    upload_res = client.post("/upload/", files=file_payload)
    job_id = upload_res.json()["job_id"]

    # Test root alias: GET /status/{job_id}
    res = client.get(f"/status/{job_id}")
    assert res.status_code == 200
    assert res.json()["job_id"] == job_id


def test_job_not_found():
    res = client.get("/upload/status/non-existent-job-uuid-1234")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_upload_unsupported_file():
    content = b"fake binary executable"
    file_payload = {"file": ("virus.exe", io.BytesIO(content), "application/x-msdownload")}
    res = client.post("/upload/", files=file_payload)
    assert res.status_code == 400
    assert "Unsupported file format" in res.json()["detail"]


def test_upload_empty_file():
    file_payload = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
    res = client.post("/upload/", files=file_payload)
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()
