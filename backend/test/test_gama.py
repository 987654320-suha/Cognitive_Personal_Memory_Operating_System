# 📁 LOCATION: backend/tests/test_gama.py
"""
test_gama.py
============
Unit tests for GAMA goal graph: detection, linking, progress reporting.
"""

import pytest
from ai.gama_service import GAMAService, detect_goals_from_text


# ── Unit: goal detection ──────────────────────────────────────────────────────

def test_detect_germany_goals():
    goals = detect_goals_from_text("I completed IELTS and preparing for Germany Masters")
    assert "Germany Masters" in goals


def test_detect_career_goals():
    goals = detect_goals_from_text("Updating my resume and cover letter for job applications")
    assert "Career" in goals


def test_detect_multiple_goals():
    goals = detect_goals_from_text("Resume for Germany Masters university application")
    assert len(goals) >= 2


def test_detect_no_goals():
    goals = detect_goals_from_text("A photo of my dog in the park")
    assert goals == []


def test_goals_are_deduplicated():
    goals = detect_goals_from_text("Germany Masters Germany university")
    assert goals.count("Germany Masters") == 1


# ── Integration: goal graph with DB ──────────────────────────────────────────

def test_ensure_goal_creates_new(db):
    svc  = GAMAService(db)
    goal = svc.ensure_goal_exists("Test Goal", "A test")
    assert goal.id is not None
    assert goal.name == "Test Goal"


def test_ensure_goal_idempotent(db):
    svc = GAMAService(db)
    g1  = svc.ensure_goal_exists("Idempotent Goal")
    g2  = svc.ensure_goal_exists("Idempotent Goal")
    assert g1.id == g2.id


def test_link_memory_to_goals(db, sample_memories):
    svc = GAMAService(db)
    detected = svc.link_memory_to_goals(
        memory_id=sample_memories[0].id,
        text_content="Resume for Germany Masters",
    )
    assert isinstance(detected, list)
    assert len(detected) > 0


def test_goal_memory_map(db, sample_goals, sample_memories):
    svc = GAMAService(db)
    gmap = svc.get_goal_memory_map()
    assert isinstance(gmap, dict)
    goal_id = sample_goals[0].id
    assert goal_id in gmap
    assert sample_memories[0].id in gmap[goal_id]


def test_get_active_goals(db, sample_goals):
    svc = GAMAService(db)
    goals = svc.get_active_goals()
    assert len(goals) >= 1
    assert all("id" in g and "name" in g for g in goals)


def test_progress_report(db, sample_goals):
    svc    = GAMAService(db)
    report = svc.get_progress_report(sample_goals[0].id)
    assert "goal" in report.to_dict()
    assert "completion_pct" in report.to_dict()
    assert "missing_hints" in report.to_dict()
    assert isinstance(report.present_memories, list)


def test_missing_docs_germany_goal(db):
    svc     = GAMAService(db)
    missing = svc._infer_missing_documents("Germany Masters", ["Resume", "IELTS Certificate"])
    assert isinstance(missing, list)
    # Should still flag missing docs (passport, APS, etc.)
    assert len(missing) > 0
