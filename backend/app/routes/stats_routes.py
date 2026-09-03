# ðŸ“ LOCATION: backend/app/routes/stats_routes.py
"""
stats_routes.py
===============
System statistics endpoints â€” powered by stats_service.py.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import get_db
from app.services.stats_service import get_full_stats

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/")
def get_stats(db: Session = Depends(get_db)):
    """
    Full system statistics including:
    - Memory totals and file type breakdown
    - Goal counts and status breakdown
    - ACMA quality metrics (avg importance, access counts)
    - Embedding and object detection coverage
    - 10 most recent memories
    """
    return get_full_stats(db)


