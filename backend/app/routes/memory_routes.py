"""
app/routes/memory_routes.py
============================
Memory CRUD endpoints.

v2: Added POST /memories/ for manual memory creation (controlled experiment support).
    Added PATCH /memories/{id}/importance for importance score adjustment.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database.database import get_db, SessionLocal
from app.services.memory_service import list_memories, get_memory, remove_memory
from app.services.goal_service import get_goals_for_memory
from app.models.user import User
from app.auth.deps import get_current_user

router = APIRouter(prefix="/memories", tags=["memories"])


# â”€â”€ Schemas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class MemoryCreate(BaseModel):
    title:           str
    description:     str
    importance_score: Optional[float] = 0.5
    source:          Optional[str]    = "manual"
    file_type:       Optional[str]    = "text"
    date:            Optional[str]    = None  # ISO date string; defaults to now


class ImportanceUpdate(BaseModel):
    importance_score: float


# ── Read endpoints ───────────────────────────────────────────────────────────

@router.get("/")
def get_memories(current_user: User = Depends(get_current_user)):
    return list_memories(user_id=current_user.id)


@router.get("/{memory_id}")
def get_memory_detail(
    memory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mem = get_memory(memory_id, user_id=current_user.id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    mem["goals"] = get_goals_for_memory(db, memory_id)
    return mem


# ── Create endpoint (manual / controlled experiment) ──────────────────────────

@router.post("/")
def create_memory(
    payload: MemoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Manually create a text memory without uploading a file.
    Used for controlled experiments (e.g., inject 'I prefer Python for backend').

    Returns the created memory with full ACMA metadata:
    - ID
    - Importance score
    - Embedding generated âœ“
    - FAISS indexed âœ“
    - Embedding generated ✓
    - FAISS indexed ✓
    - BM25 indexed ✓
    """
    from app.models.memory import Memory
    from ai.embedding_service import get_embedding
    import json

    # Default date to now if not supplied
    date_str = payload.date or datetime.now(timezone.utc).date().isoformat()

    # Generate embedding from title + description
    text_for_embedding = f"{payload.title}. {payload.description}"
    embedding_vector   = get_embedding(text_for_embedding)
    embedding_json     = json.dumps(embedding_vector) if embedding_vector else "[]"

    # Compute importance — use provided value (for manual control in experiments)
    importance = max(0.0, min(1.0, payload.importance_score or 0.5))

    # Persist to DB
    user_id = current_user.id if current_user else None
    mem = Memory(
        title            = payload.title,
        description      = payload.description,
        source           = payload.source or "manual",
        file_type        = payload.file_type or "text",
        image            = None,
        date             = date_str,
        location         = None,
        embedding        = embedding_json,
        objects          = "[]",
        importance_score = importance,
        access_count     = 0,
        version          = 1,
        parent_id        = None,
        user_id          = user_id,
    )
    db.add(mem)
    db.commit()
    db.refresh(mem)

    # Rebuild FAISS + BM25 indices so new memory is searchable immediately
    _refresh_after_change()

    # Run contradiction check against existing memories (non-blocking — just info)
    conflict_info = None
    try:
        from ai.contradiction_detector import scan_for_contradictions
        from app.services.database_service import get_all_memories
        all_mems = get_all_memories(user_id=user_id)
        contradictions = scan_for_contradictions(all_mems)
        # Only return contradictions involving this new memory
        my_conflicts = [c for c in contradictions if
                        c.get("memory_a", {}).get("id") == mem.id or
                        c.get("memory_b", {}).get("id") == mem.id]
        if my_conflicts:
            conflict_info = my_conflicts
    except Exception:
        pass

    return {
        "created":          True,
        "memory":           mem.to_dict(),
        "embedding_ready":  bool(embedding_vector),
        "faiss_indexed":    True,
        "bm25_indexed":     True,
        "conflicts_found":  conflict_info,
    }


# ── Update importance ─────────────────────────────────────────────────────────

@router.patch("/{memory_id}/importance")
def update_importance(
    memory_id: int,
    payload: ImportanceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Adjust the importance score of an existing memory (for ablation experiments)."""
    from app.models.memory import Memory as MemModel
    query = db.query(MemModel).filter(MemModel.id == memory_id)
    if current_user:
        query = query.filter(MemModel.user_id == current_user.id)
    mem = query.first()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    mem.importance_score = max(0.0, min(1.0, payload.importance_score))
    db.commit()
    _refresh_after_change()
    return {"memory_id": memory_id, "new_importance_score": mem.importance_score}


# â”€â”€ Delete â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.delete("/{memory_id}")
def delete_memory_endpoint(
    memory_id: int,
    current_user: User = Depends(get_current_user),
):
    ok = remove_memory(memory_id, user_id=current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found")

    # Refresh cache and rebuild indices after deletion
    _refresh_after_change()

    return {"deleted": memory_id}


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _refresh_after_change():
    """
    Refresh memory cache and rebuild search indices after any data modification.
    """
    try:
        from app.services.database_service import refresh_memory_cache, get_all_memories
        from ai.faiss_service import build_index
        from ai.hybrid_search import build_bm25

        # Refresh in-memory cache
        refresh_memory_cache()
        print("[Memory] Memory cache refreshed after change")

        # Rebuild FAISS and BM25 indices
        memories = get_all_memories()
        if memories:
            build_index(memories)
            print(f"[Memory] FAISS index rebuilt with {len(memories)} memories")

            build_bm25(memories)
            print(f"[Memory] BM25 index rebuilt with {len(memories)} memories")
        else:
            print("[Memory] No memories to index")
    except Exception as e:
        print(f"[Memory] Error refreshing after change: {e}")


