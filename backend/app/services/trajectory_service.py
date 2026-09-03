# ðŸ“ LOCATION: backend/app/services/trajectory_service.py
"""
trajectory_service.py
=======================
Service layer for the Predictive Goal Engine.
Combines GAMA progress reports with trajectory projection.
"""

from __future__ import annotations
from sqlalchemy.orm import Session

from ai.predictive_goal_engine import compute_all_trajectories
from ai.gama_service import GAMAService


def get_all_trajectories(db: Session) -> list[dict]:
    """
    Computes predictive trajectories for every active goal.
    Returns next recommended action + projected completion date for each.
    """
    gama = GAMAService(db)
    active_goals = gama.get_active_goals()

    progress_reports = {}
    for goal in active_goals:
        try:
            report = gama.get_progress_report(goal["id"])
            progress_reports[goal["name"]] = report.to_dict()
        except Exception:
            continue

    return compute_all_trajectories(active_goals, progress_reports)


def get_trajectory_for_goal(db: Session, goal_id: int) -> dict:
    """Returns the trajectory for a single goal by ID."""
    gama = GAMAService(db)
    report = gama.get_progress_report(goal_id)
    report_dict = report.to_dict()
    goal_name = report_dict["goal"]["name"]

    from ai.predictive_goal_engine import PredictiveGoalEngine
    engine = PredictiveGoalEngine()
    trajectory = engine.compute_trajectory(goal_name, report_dict["present"])
    return trajectory.to_dict()


