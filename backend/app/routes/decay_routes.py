# ðŸ“ LOCATION: backend/app/routes/decay_routes.py
"""
decay_routes.py
=================
API endpoints for the Context Decay Model â€” adaptive forgetting curve
with cross-memory reinforcement propagation.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import get_db
from app.services.decay_service import reinforce_memory, get_decay_score
from app.models.decay_state import DecayState

router = APIRouter(prefix="/decay", tags=["decay"])


@router.post("/reinforce/{memory_id}")
def reinforce(memory_id: int, db: Session = Depends(get_db)):
    """
    Manually reinforce a memory (normally called automatically
    when a memory is retrieved via search or chat).
    Also propagates a partial reinforcement to graph neighbors.
    """
    from app.models.memory import Memory
    mem = db.query(Memory).filter(Memory.id == memory_id).first()
    if not mem:
        return {"error": "Memory not found"}

    state = reinforce_memory(db, memory_id, mem.title or "", mem.description or "")
    return {"memory_id": memory_id, "decay_state": state}


@router.get("/score/{memory_id}")
def get_score(memory_id: int, db: Session = Depends(get_db)):
    """Returns the current decay-adjusted relevance score for a memory."""
    from app.models.memory import Memory
    mem = db.query(Memory).filter(Memory.id == memory_id).first()
    if not mem:
        return {"error": "Memory not found"}

    score = get_decay_score(db, memory_id, mem.date or "", mem.title or "")
    return {"memory_id": memory_id, "decay_score": round(score, 4)}


@router.get("/states")
def list_decay_states(db: Session = Depends(get_db)):
    """Returns all persisted decay states â€” useful for debugging/research."""
    states = db.query(DecayState).all()
    return {"count": len(states), "states": [s.to_dict() for s in states]}


