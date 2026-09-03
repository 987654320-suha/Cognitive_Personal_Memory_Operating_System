# ðŸ“ LOCATION: backend/app/routes/timeline_routes.py
"""
timeline_routes.py
==================
Timeline endpoints â€” memories grouped and ordered by date.
Powers the Timeline page in the frontend.
"""

from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from collections import defaultdict

from database.database import get_db
from app.models.memory import Memory
from app.services.search_service import date_range_search

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("/")
def get_timeline(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Returns all memories sorted by date descending, grouped by month.
    Response shape:
        {
            "groups": [
                { "month": "June 2025", "memories": [...] },
                ...
            ]
        }
    """
    memories = (
        db.query(Memory)
        .order_by(Memory.date.desc())
        .limit(limit)
        .all()
    )

    groups: dict[str, list[dict]] = defaultdict(list)

    for m in memories:
        date_str = m.date or ""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            month_key = dt.strftime("%B %Y")
        except Exception:
            month_key = "Unknown date"

        groups[month_key].append({
            "id":          m.id,
            "title":       m.title,
            "description": m.description,
            "image":       m.image,
            "date":        m.date,
            "file_type":   m.file_type,
            "location":    m.location,
        })

    ordered = [
        {"month": month, "memories": mems}
        for month, mems in groups.items()
    ]

    return {"total": len(memories), "groups": ordered}


@router.get("/range")
def timeline_range(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end:   str = Query(..., description="End date YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """Return memories within a specific date range."""
    results = date_range_search(db, start, end)
    return {"start": start, "end": end, "count": len(results), "results": results}


@router.get("/recent")
def recent_memories(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return the N most recently added memories."""
    memories = (
        db.query(Memory)
        .order_by(Memory.date.desc())
        .limit(limit)
        .all()
    )
    return [m.to_dict() for m in memories]


