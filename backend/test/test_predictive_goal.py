# 📁 LOCATION: backend/tests/test_predictive_goal.py
"""
test_predictive_goal.py
=========================
Tests for the Predictive Goal Trajectory Engine.
"""

from ai.predictive_goal_engine import PredictiveGoalEngine


def test_trajectory_with_known_sequence():
    engine = PredictiveGoalEngine()
    present = [
        {"title": "IELTS Certificate", "date": "2024-01-01"},
        {"title": "Resume CV", "date": "2024-02-01"},
    ]
    trajectory = engine.compute_trajectory("Germany Masters", present)
    assert trajectory.goal_name == "Germany Masters"
    assert len(trajectory.sequence) > 0
    assert trajectory.next_recommended is not None


def test_velocity_computed_from_dates():
    engine = PredictiveGoalEngine()
    present = [
        {"title": "Bachelor's degree certificate", "date": "2024-01-01"},
        {"title": "Transcripts", "date": "2024-02-01"},
        {"title": "IELTS certificate", "date": "2024-03-01"},
    ]
    trajectory = engine.compute_trajectory("Germany Masters", present)
    assert trajectory.velocity_days_per_doc is not None
    assert trajectory.velocity_days_per_doc > 0


def test_no_velocity_with_single_document():
    engine = PredictiveGoalEngine()
    present = [{"title": "IELTS certificate", "date": "2024-01-01"}]
    trajectory = engine.compute_trajectory("Germany Masters", present)
    assert trajectory.velocity_days_per_doc is None


def test_fallback_for_unknown_goal():
    engine = PredictiveGoalEngine()
    trajectory = engine.compute_trajectory("Random Unknown Goal", [])
    assert trajectory.sequence == []
    assert trajectory.confidence < 0.5


def test_fully_complete_goal_has_no_next_recommended():
    engine = PredictiveGoalEngine()
    present = [
        {"title": "Passport", "date": "2024-01-01"},
        {"title": "Visa application", "date": "2024-02-01"},
        {"title": "Ticket booking", "date": "2024-03-01"},
        {"title": "Hotel booking", "date": "2024-04-01"},
    ]
    trajectory = engine.compute_trajectory("Travel / Visa", present)
    assert trajectory.next_recommended is None
