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
