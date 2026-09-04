# ðŸ“ LOCATION: backend/app/routes/stats_routes.py
"""
stats_routes.py
===============
System statistics endpoints â€” powered by stats_service.py.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from typing import Optional
from database.database import get_db
from app.services.stats_service import get_full_stats
from app.models.user import User
from app.auth.deps import get_optional_current_user

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/")
def get_stats(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Full system statistics scoped to the authenticated user.
    """
    user_id = current_user.id if current_user else None
    return get_full_stats(db, user_id=user_id)


