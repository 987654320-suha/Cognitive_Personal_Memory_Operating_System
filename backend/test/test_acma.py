# 📁 LOCATION: backend/tests/test_acma.py
"""
test_acma.py
============
Unit tests for the ACMA engine — activation scoring and ranking.
"""

import json
import pytest
from ai.acma_engine import ACMAEngine, DEFAULT_WEIGHTS


@pytest.fixture
def engine():
    return ACMAEngine()


@pytest.fixture
def mock_faiss_results():
    return [
        {"id": 1, "title": "Resume", "description": "Resume doc",
         "score": 0.9, "image": None, "date": "2024-06-01", "location": None, "objects": "[]"},
        {"id": 2, "title": "IELTS", "description": "IELTS cert",
         "score": 0.7, "image": None, "date": "2024-01-01", "location": None, "objects": '["certificate"]'},
        {"id": 3, "title": "Car Photo", "description": "A car",
         "score": 0.3, "image": "/uploads/car.jpg", "date": "2023-01-01", "location": None, "objects": '["car"]'},
    ]


@pytest.fixture
def mock_all_memories(mock_faiss_results):
    mems = []
    for r in mock_faiss_results:
        m = dict(r)
        m["embedding"] = json.dumps([0.1] * 384)
        m["importance_score"] = 0.8 if r["id"] in (1, 2) else 0.2
        m["access_count"] = 5 if r["id"] == 1 else 0
        mems.append(m)
    return mems


def test_rank_returns_sorted_results(engine, mock_faiss_results, mock_all_memories):
    results = engine.rank(
        query="germany preparation",
        faiss_results=mock_faiss_results,
        all_memories=mock_all_memories,
        active_goals=[{"id": 1, "name": "Germany Masters", "description": ""}],
        goal_memory_map={1: [1, 2]},
    )
    assert len(results) == 3
    scores = [r.activation_score for r in results]
    assert scores == sorted(scores, reverse=True), "Results must be sorted descending"


def test_goal_linked_memory_scores_higher(engine, mock_faiss_results, mock_all_memories):
    results = engine.rank(
        query="university application",
        faiss_results=mock_faiss_results,
        all_memories=mock_all_memories,
        active_goals=[{"id": 1, "name": "Germany Masters", "description": ""}],
        goal_memory_map={1: [1, 2]},
    )
    goal_ids = {r.memory_id for r in results if r.goal_score > 0}
    no_goal_ids = {r.memory_id for r in results if r.goal_score == 0}
    assert 1 in goal_ids
    assert 3 in no_goal_ids


def test_all_component_scores_between_0_and_1(engine, mock_faiss_results, mock_all_memories):
    results = engine.rank(
        query="test",
        faiss_results=mock_faiss_results,
        all_memories=mock_all_memories,
        active_goals=[],
        goal_memory_map={},
    )
    for r in results:
        assert 0.0 <= r.semantic_score     <= 1.0
        assert 0.0 <= r.goal_score         <= 1.0
        assert 0.0 <= r.relationship_score <= 1.0
        assert 0.0 <= r.importance_score   <= 1.0
        assert 0.0 <= r.temporal_score     <= 1.0
        assert 0.0 <= r.access_score       <= 1.0
        assert 0.0 <= r.activation_score   <= 1.0


def test_weights_sum_to_one():
    total = sum(DEFAULT_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-6


def test_custom_weights(mock_faiss_results, mock_all_memories):
    custom = {"semantic": 1.0, "goal": 0.0, "relationship": 0.0,
              "importance": 0.0, "temporal": 0.0, "access": 0.0}
    engine = ACMAEngine(weights=custom)
    results = engine.rank(
        query="test",
        faiss_results=mock_faiss_results,
        all_memories=mock_all_memories,
        active_goals=[],
        goal_memory_map={},
    )
    # With only semantic, ranking should match FAISS score order
    assert results[0].memory_id == 1   # highest FAISS score
