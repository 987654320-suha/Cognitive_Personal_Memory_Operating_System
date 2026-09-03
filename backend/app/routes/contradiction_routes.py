# ðŸ“ LOCATION: backend/app/routes/contradiction_routes.py
"""
contradiction_routes.py
=========================
API endpoints for the Cross-Memory Contradiction Detector.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import get_db
from app.services.contradiction_service import (
    run_contradiction_scan,
    get_contradictions_for_memory,
)

router = APIRouter(prefix="/contradictions", tags=["contradictions"])


@router.get("/")
def scan_contradictions(db: Session = Depends(get_db)):
    """
    Scans all memories for conflicting facts (different phone numbers,
    addresses, dates etc. across documents).
    Returns contradictions grouped by classification:
      - likely_error: same time period, probably a typo
      - legitimate_update: large time gap, probably an intentional change
      - needs_review: insufficient data to classify automatically
    """
    return run_contradiction_scan(db)


@router.get("/memory/{memory_id}")
def get_memory_contradictions(memory_id: int, db: Session = Depends(get_db)):
    """Returns all contradictions involving a specific memory."""
    return {
        "memory_id": memory_id,
        "contradictions": get_contradictions_for_memory(db, memory_id),
    }


