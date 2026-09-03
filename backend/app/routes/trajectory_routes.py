# ðŸ“ LOCATION: backend/app/routes/trajectory_routes.py
"""
trajectory_routes.py
======================
API endpoints for the Predictive Goal Trajectory Engine.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from app.services.trajectory_service import get_all_trajectories, get_trajectory_for_goal

router = APIRouter(prefix="/trajectories", tags=["trajectories"])


@router.get("/")
def list_trajectories(db: Session = Depends(get_db)):
    """
    Returns predictive trajectories for all active goals:
    document sequence progress, velocity, next recommended action,
    and projected completion date.
    """
    return {"trajectories": get_all_trajectories(db)}


@router.get("/{goal_id}")
def get_goal_trajectory(goal_id: int, db: Session = Depends(get_db)):
    """Returns the predictive trajectory for a single goal."""
    try:
        return get_trajectory_for_goal(db, goal_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


