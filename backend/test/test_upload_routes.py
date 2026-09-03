import io
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


def test_upload_text_file():
    content = b"This is a test document about Python FastAPI and Cognitive Memory Sync."
    file_payload = {"file": ("test_doc.txt", io.BytesIO(content), "text/plain")}
    res = client.post("/upload/", files=file_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "memory" in data
    assert data["memory"]["id"] > 0
    assert "processing_time" in data


def test_upload_markdown_file():
    content = b"# Notes on Machine Learning\n\nFAISS vector search and BM25 hybrid ranking."
    file_payload = {"file": ("notes.md", io.BytesIO(content), "text/markdown")}
    res = client.post("/upload/", files=file_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["memory"]["id"] > 0


def test_upload_unsupported_file():
    content = b"fake binary exe data"
    file_payload = {"file": ("malicious.exe", io.BytesIO(content), "application/x-msdownload")}
    res = client.post("/upload/", files=file_payload)
    assert res.status_code == 400
    assert "Unsupported file format" in res.json()["detail"]


def test_upload_empty_file():
    file_payload = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
    res = client.post("/upload/", files=file_payload)
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()
