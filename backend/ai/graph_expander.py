"""
graph_expander.py
Expands retrieved memories using the memory relationship graph.
"""

from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.relationship import MemoryRelationship
from app.models.memory import Memory


def expand_memories(
    db: Session,
    memories: list[dict],
    max_related: int = 2,
) -> list[dict]:

    expanded = list(memories)

    existing = {m["id"] for m in memories}

    for mem in memories:

        relationships = (
            db.query(MemoryRelationship)
            .filter(
                MemoryRelationship.source_memory_id == mem["id"]
            )
            .limit(max_related)
            .all()
        )

        for rel in relationships:

            if rel.target_memory_id in existing:
                continue

            target = (
                db.query(Memory)
                .filter(Memory.id == rel.target_memory_id)
                .first()
            )

            if target:

                existing.add(target.id)

                d = target.to_dict()

                d["relationship_type"] = rel.relationship_type

                d["relationship_strength"] = rel.strength

                expanded.append(d)

    return expanded


