"""
app/routes/memory_update_routes.py
====================================
Memory update endpoints with versioning and contradiction pre-check.

Endpoints:
  PUT  /memories/{id}/update   â€” Update memory content, saving old version to history
  GET  /memories/{id}/history  â€” Retrieve version history for a memory

These endpoints are critical for:
  - Memory update experiment
  - Temporal validity experiment
  - Contradiction detection experiment
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database.database import get_db

router = APIRouter(prefix="/memories", tags=["memory-update"])


# â”€â”€ Schemas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class MemoryUpdate(BaseModel):
    title:            Optional[str]   = None
    description:      Optional[str]   = None
    importance_score: Optional[float] = None
    date:             Optional[str]   = None    # Override date for temporal experiments
    change_reason:    Optional[str]   = "manual_update"


# â”€â”€ Update with versioning â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.put("/{memory_id}/update")
def update_memory(memory_id: int, payload: MemoryUpdate, db: Session = Depends(get_db)):
    """
    Update a memory's content.

    Before saving:
      1. Archives the current version to memory_history
      2. Runs contradiction check between old and new content
      3. Updates the memory record (bumps version number)
      4. Rebuilds FAISS + BM25 indices

    Returns:
      - Updated memory
      - Old version snapshot
      - Contradiction analysis (if any conflict detected)
    """
    from app.models.memory import Memory
    from app.models.memory_history import MemoryHistory
    from ai.embedding_service import get_embedding
    from ai.contradiction_detector import scan_for_contradictions
    from app.services.database_service import get_all_memories
    import json

    # Fetch existing memory
    mem = db.query(Memory).filter(Memory.id == memory_id).first()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")

    # â”€â”€ 1. Archive current version to history â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    now_iso = datetime.now(timezone.utc).isoformat()
    history_record = MemoryHistory(
        memory_id        = mem.id,
        version          = mem.version or 1,
        title            = mem.title,
        description      = mem.description,
        importance_score = mem.importance_score,
        source           = mem.source,
        file_type        = mem.file_type,
        date             = mem.date,
        archived_at      = now_iso,
        change_reason    = payload.change_reason or "manual_update",
    )
    db.add(history_record)

    # â”€â”€ 2. Detect contradictions between old and new content â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    old_content = f"{mem.title} {mem.description}"
    new_title   = payload.title       if payload.title is not None       else mem.title
    new_desc    = payload.description if payload.description is not None else mem.description
    new_content = f"{new_title} {new_desc}"

    conflict_info = None
    try:
        # Build a temporary "new" memory dict to compare with all existing ones
        temp_new = {
            "id":          -1,          # Placeholder id
            "title":       new_title,
            "description": new_desc,
            "date":        payload.date or mem.date,
        }
        # Compare against the OLD version specifically
        temp_old = {
            "id":          mem.id,
            "title":       mem.title,
            "description": mem.description,
            "date":        mem.date,
        }
        contradictions = scan_for_contradictions([temp_old, temp_new])
        if contradictions:
            conflict_info = contradictions
    except Exception as e:
        print(f"[MemoryUpdate] Contradiction check error: {e}")

    # â”€â”€ 3. Apply updates â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if payload.title is not None:
        mem.title = payload.title
    if payload.description is not None:
        mem.description = payload.description
    if payload.importance_score is not None:
        mem.importance_score = max(0.0, min(1.0, payload.importance_score))
    if payload.date is not None:
        mem.date = payload.date

    mem.version = (mem.version or 1) + 1

    # Re-generate embedding for updated content
    text_for_embedding = f"{mem.title}. {mem.description}"
    new_embedding = get_embedding(text_for_embedding)
    if new_embedding:
        mem.embedding = json.dumps(new_embedding)

    db.commit()
    db.refresh(mem)

    # â”€â”€ 4. Rebuild indices â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _refresh_after_change()

    return {
        "updated":           True,
        "memory":            mem.to_dict(),
        "previous_version":  history_record.to_dict(),
        "conflicts_detected": conflict_info,
        "embedding_updated": bool(new_embedding),
    }


# â”€â”€ Version history â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/{memory_id}/history")
def get_memory_history(memory_id: int, db: Session = Depends(get_db)):
    """
    Returns all previous versions of a memory, ordered oldest â†’ newest.

    Used for:
      - Temporal experiment: verify system retrieves latest version
      - Update experiment: confirm old versions are preserved
    """
    from app.models.memory import Memory
    from app.models.memory_history import MemoryHistory

    # Check memory exists
    mem = db.query(Memory).filter(Memory.id == memory_id).first()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")

    # Get all history records
    history = (
        db.query(MemoryHistory)
        .filter(MemoryHistory.memory_id == memory_id)
        .order_by(MemoryHistory.version.asc())
        .all()
    )

    return {
        "memory_id":       memory_id,
        "current_version": mem.version or 1,
        "current": {
            "version":          mem.version or 1,
            "title":            mem.title,
            "description":      mem.description,
            "importance_score": mem.importance_score,
            "date":             mem.date,
            "is_current":       True,
        },
        "history": [h.to_dict() for h in history],
        "total_versions": len(history) + 1,
    }


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _refresh_after_change():
    try:
        from app.services.database_service import refresh_memory_cache, get_all_memories
        from ai.faiss_service import build_index
        from ai.hybrid_search import build_bm25

        refresh_memory_cache()
        memories = get_all_memories()
        if memories:
            build_index(memories)
            build_bm25(memories)
    except Exception as e:
        print(f"[MemoryUpdate] Error refreshing after change: {e}")


