# ðŸ“ LOCATION: backend/app/routes/graph_routes.py
"""
graph_routes.py
===============
Memory relationship graph endpoints for frontend visualization.
Provides nodes + edges for D3.js / Cytoscape graph rendering.
"""

from fastapi import APIRouter, Depends, BackgroundTasks, Query
from sqlalchemy.orm import Session

from database.database import get_db
from app.services.graph_service import rebuild_graph, get_graph, get_neighbors

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/")
def get_memory_graph(db: Session = Depends(get_db)):
    """
    Returns the full memory relationship graph.
    Shape: { nodes: [...], edges: [...], stats: {...} }
    Use this to render a force-directed graph in the frontend.
    """
    return get_graph(db)


@router.post("/rebuild")
def rebuild_memory_graph(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Rebuilds the relationship graph from scratch.
    Runs in background â€” can take a few seconds for large collections.
    """
    background_tasks.add_task(_rebuild_task)
    return {"message": "Graph rebuild started in background"}


@router.get("/neighbors/{memory_id}")
def get_memory_neighbors(
    memory_id: int,
    top_k: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Returns the top_k most strongly connected memories to a given memory.
    Used for the 'Related Memories' panel in the detail view.
    """
    neighbors = get_neighbors(db, memory_id, top_k=top_k)
    return {"memory_id": memory_id, "neighbors": neighbors}


@router.get("/patterns")
def detect_patterns():
    """
    Detects recurring memory patterns (e.g. monthly documents).
    Useful for showing the user automatic insights.
    """
    from ai.temporal_reasoner import detect_recurring_patterns
    from app.services.database_service import get_all_memories
    memories = get_all_memories()
    patterns = detect_recurring_patterns(memories)
    return {"patterns": patterns}


def _rebuild_task():
    from database.database import SessionLocal
    db = SessionLocal()
    try:
        stats = rebuild_graph(db)
        print(f"[Graph] Rebuild complete: {stats}")
    finally:
        db.close()


