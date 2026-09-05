# 📁 LOCATION: backend/tests/test_search.py
"""
test_search.py
==============
Tests for search modes: keyword, object, combined, ACMA API.
"""

import pytest
from unittest.mock import patch

from backend.app.services.search_service import keyword_search, object_search


def test_keyword_search_finds_match(db, sample_memories):
    results = keyword_search("resume", db, top_k=10)
    titles = [r["title"] for r in results]
    assert any("Resume" in t for t in titles)


def test_keyword_search_no_match(db, sample_memories):
    results = keyword_search("xxxxxxxxnotexist", db)
    assert results == []


def test_object_search_finds_match(db, sample_memories):
    results = object_search("car", db, top_k=10)
    titles = [r["title"] for r in results]
    assert any("Car" in t for t in titles)


def test_object_search_no_match(db, sample_memories):
    results = object_search("xxxxxxxxnotexist", db)
    assert results == []


def test_search_api_keyword_mode(client, sample_memories):
    response = client.get("/search/?q=resume&mode=keyword")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert data["mode"] == "keyword"


def test_search_api_fast_mode(client, sample_memories):
    with patch("app.routes.search_routes.semantic_search", return_value=[]):
        response = client.get("/search/?q=resume&mode=fast")
    assert response.status_code == 200


def test_search_explain_endpoint(client, sample_memories):
    with patch("app.routes.search_routes.acma_search", return_value=[
        {"id": 1, "title": "Resume 2024", "activation_score": 0.8,
         "components": {}, "matched_goals": [], "activation_reason": "test"}
    ]):
        response = client.get("/search/explain/1?q=resume")
    assert response.status_code == 200
    data = response.json()
    assert data.get("in_results") is True or "activation" in data


def test_acma_search_preserves_user_id_and_filters():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    import time
    user_email = f"search_user_{int(time.time()*1000)}@cognisphere.ai"
    reg = client.post("/auth/register", json={"email": user_email, "password": "Password123!"})
    assert reg.status_code == 201
    token = reg.json()["token"]
    user_id = reg.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create memory for this user
    mem_res = client.post(
        "/memories/",
        json={"title": "Target Document", "description": "Doc for user 1", "source": "target.txt"},
        headers=headers,
    )
    assert mem_res.status_code == 200
    m1_id = mem_res.json()["memory"]["id"]

    # Search with ACMA mode
    res = client.get("/search/?q=Target&mode=acma", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert all(r.get("user_id") == user_id for r in data["results"])
    assert any(r["id"] == m1_id for r in data["results"])

