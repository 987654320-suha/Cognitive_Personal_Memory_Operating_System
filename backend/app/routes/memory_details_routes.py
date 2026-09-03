# ðŸ“ LOCATION: backend/app/routes/memory_details_routes.py
"""
memory_details_routes.py
========================
Rich memory detail endpoints â€” full metadata, related memories,
ACMA activation trace, and linked goals.
Powers the Memory Detail page in the frontend.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from database.database import get_db
from app.models.memory import Memory
from app.services.goal_service import get_goals_for_memory
from ai.semantic_search import acma_search

router = APIRouter(prefix="/memory-details", tags=["memory-details"])


@router.get("/{memory_id}")
def get_memory_detail(memory_id: int, db: Session = Depends(get_db)):
    """
    Full memory detail with:
    - All metadata fields
    - Linked goals
    - ACMA scores (if the memory has been retrieved before)
    """
    mem = db.query(Memory).filter(Memory.id == memory_id).first()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")

    detail = mem.to_dict()
    detail["goals"] = get_goals_for_memory(db, memory_id)
    return detail


@router.get("/{memory_id}/related")
def get_related_memories(
    memory_id: int,
    top_k: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    Finds memories most semantically similar to the given memory.
    Uses the memory's own title+description as the query.
    """
    mem = db.query(Memory).filter(Memory.id == memory_id).first()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")

    query_text = f"{mem.title or ''} {mem.description or ''}"
    if not query_text.strip():
        return {"memory_id": memory_id, "related": []}

    results = acma_search(query_text, db, top_k=top_k + 1)

    # Exclude the memory itself
    related = [r for r in results if r["id"] != memory_id][:top_k]
    return {"memory_id": memory_id, "related": related}


@router.get("/{memory_id}/activation")
def get_activation_trace(
    memory_id: int,
    query: str = Query(..., description="The search query to compute activation for"),
    db: Session = Depends(get_db),
):
    """
    Returns the ACMA activation breakdown for a specific memory
    given a query. Shows exactly why this memory was (or wasn't) retrieved.
    """
    results = acma_search(query, db, top_k=100)
    match = next((r for r in results if r["id"] == memory_id), None)

    if not match:
        return {
            "memory_id": memory_id,
            "query": query,
            "in_results": False,
            "message": "Memory was not activated for this query",
        }

    return {
        "memory_id":   memory_id,
        "query":       query,
        "in_results":  True,
        "rank":        next((i + 1 for i, r in enumerate(results) if r["id"] == memory_id), None),
        "activation":  match,
    }


