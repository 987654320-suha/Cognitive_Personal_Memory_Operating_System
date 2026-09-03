# 📁 LOCATION: backend/tests/test_pipeline.py
"""
test_pipeline.py
================
Integration tests for the memory ingestion pipeline.
Uses temporary files — no real uploads directory needed.
"""

import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock


def make_temp_text_file(content: str, suffix: str = ".txt") -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    return f.name


def test_pipeline_creates_memory(db):
    """End-to-end: pipeline saves a memory to DB."""
    tmp = make_temp_text_file("This is my resume with Python skills")

    try:
        with patch("ai.memory_pipeline.SessionLocal", return_value=db), \
             patch("ai.memory_pipeline._update_faiss"), \
             patch("ai.memory_pipeline.GAMAService") as mock_gama:

            mock_gama.return_value.link_memory_to_goals.return_value = ["Career"]

            from ai.memory_pipeline import run_pipeline
            result = run_pipeline(tmp, source_hint="Resume")

        assert "id" in result
        assert result["title"] == "Resume"
        assert result["file_type"] == "txt"
        assert isinstance(result.get("embedding"), list)
    finally:
        os.unlink(tmp)


def test_pipeline_detects_goals(db):
    """Pipeline should detect goals from text content."""
    tmp = make_temp_text_file("IELTS certificate Germany Masters university application")

    try:
        with patch("ai.memory_pipeline.SessionLocal", return_value=db), \
             patch("ai.memory_pipeline._update_faiss"):

            from ai.memory_pipeline import run_pipeline
            result = run_pipeline(tmp)

        assert "detected_goals" in result
        assert isinstance(result["detected_goals"], list)
    finally:
        os.unlink(tmp)


def test_pipeline_rejects_missing_file():
    from ai.memory_pipeline import run_pipeline
    with pytest.raises(FileNotFoundError):
        run_pipeline("/nonexistent/path/file.pdf")


def test_importance_scorer_high_value():
    from ai.importance_scorer import score_importance
    score = score_importance("IELTS Certificate 2024", "IELTS overall band score 7.5")
    assert score > 0.5


def test_importance_scorer_low_value():
    from ai.importance_scorer import score_importance
    score = score_importance("screenshot", "random screenshot of desktop")
    assert score < 0.5
