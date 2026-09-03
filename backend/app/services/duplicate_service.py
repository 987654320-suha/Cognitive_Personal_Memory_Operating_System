# ðŸ“ LOCATION: backend/app/services/duplicate_service.py
"""
duplicate_service.py
====================
Service layer for duplicate detection.
Wraps ai/duplicate_detector.py with DB queries.
"""

from __future__ import annotations
from sqlalchemy.orm import Session

from ai.duplicate_detector import scan_all_duplicates, find_semantic_duplicates
from app.services.database_service import get_all_memories


def find_all_duplicates(db: Session) -> dict:
    """
    Scans all memories for duplicates.
    Returns pairs with similarity scores.
    """
    memories = get_all_memories()
    pairs    = scan_all_duplicates(memories)
    return {
        "total_memories": len(memories),
        "duplicate_pairs": len(pairs),
        "pairs": pairs,
    }


def check_before_save(new_embedding: list[float], db: Session) -> list[dict]:
    """
    Called by memory_pipeline before saving a new memory.
    Returns list of near-duplicate existing memories (may be empty).
    """
    memories = get_all_memories()
    return find_semantic_duplicates(new_embedding, memories)


def delete_duplicate(db: Session, keep_id: int, delete_id: int) -> bool:
    """
    Deletes the duplicate memory, keeping the preferred one.
    Also removes all goal_memory edges for the deleted memory.
    """
    from app.models.memory import Memory
    from app.models.goal_memory import GoalMemory

    mem = db.query(Memory).filter(Memory.id == delete_id).first()
    if not mem:
        return False

    db.query(GoalMemory).filter(GoalMemory.memory_id == delete_id).delete()
    db.delete(mem)
    db.commit()
    return True


