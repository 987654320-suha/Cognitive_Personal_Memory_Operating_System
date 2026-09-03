# ðŸ“ LOCATION: backend/app/services/decay_service.py
"""
decay_service.py
==================
Service layer for the Context Decay Model.
Persists decay state to DB and integrates with ACMA scoring.
"""

from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ai.context_decay_model import ContextDecayModel
from app.models.decay_state import DecayState


def reinforce_memory(db: Session, memory_id: int, title: str, description: str = "") -> dict:
    """
    Called whenever a memory is retrieved/accessed.
    Updates the persisted decay state and propagates to graph neighbors.
    """
    model = ContextDecayModel()

    # Load existing state from DB if present
    existing = db.query(DecayState).filter(DecayState.memory_id == memory_id).first()
    category = model.classify_category(title, description)

    if existing:
        model._state[memory_id] = _row_to_state(existing)

    state = model.reinforce(memory_id, category=category)
    _persist_state(db, state, category)

    # Propagate to graph neighbors
    try:
        from app.services.graph_service import get_neighbors
        neighbors = get_neighbors(db, memory_id, top_k=5)
        neighbor_ids = [n["id"] for n in neighbors]
        category_lookup = {n["id"]: model.classify_category(n.get("title", "")) for n in neighbors}
        propagated = model.propagate_reinforcement(memory_id, neighbor_ids, category_lookup)
        for p_state in propagated:
            _persist_state(db, p_state, category_lookup.get(p_state.memory_id, "default"))
    except Exception as e:
        print(f"[DecayService] Propagation skipped: {e}")

    return state.to_dict()


def get_decay_score(db: Session, memory_id: int, created_date: str, title: str = "") -> float:
    """Returns the decay-adjusted relevance score for a memory."""
    model = ContextDecayModel()
    existing = db.query(DecayState).filter(DecayState.memory_id == memory_id).first()
    category = model.classify_category(title)

    if existing:
        model._state[memory_id] = _row_to_state(existing)

    return model.decay_score(memory_id, created_date, category)


def _persist_state(db: Session, state, category: str):
    row = db.query(DecayState).filter(DecayState.memory_id == state.memory_id).first()
    if row is None:
        row = DecayState(
            memory_id=state.memory_id,
            last_reinforced=state.last_reinforced.isoformat(),
            reinforcement_count=state.reinforcement_count,
            effective_half_life=state.effective_half_life,
            category=category,
        )
        db.add(row)
    else:
        row.last_reinforced     = state.last_reinforced.isoformat()
        row.reinforcement_count = state.reinforcement_count
        row.effective_half_life = state.effective_half_life
        row.category            = category
    db.commit()


def _row_to_state(row: DecayState):
    from ai.context_decay_model import DecayState as ModelState
    return ModelState(
        memory_id=row.memory_id,
        last_reinforced=datetime.fromisoformat(row.last_reinforced),
        reinforcement_count=row.reinforcement_count,
        effective_half_life=row.effective_half_life,
    )


