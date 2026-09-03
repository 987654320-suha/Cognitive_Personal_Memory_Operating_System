# ðŸ“ LOCATION: backend/app/services/graph_service.py
"""
graph_service.py
================
Service layer for building, persisting, and querying
the Memory Relationship Graph (graph_builder.py â†’ SQLite).
"""

from __future__ import annotations
from sqlalchemy.orm import Session

from ai.graph_builder import build_memory_graph
from app.models.relationship import MemoryRelationship
from app.services.database_service import get_all_memories


def rebuild_graph(db: Session) -> dict:
    """
    Rebuilds the full relationship graph from all memories and persists to DB.
    Returns graph stats.
    """
    memories = get_all_memories()
    graph    = build_memory_graph(memories)

    # Clear existing edges
    db.query(MemoryRelationship).delete()

    # Persist new edges
    for edge in graph.edges:
        rel = MemoryRelationship(
            source_id=edge["source"],
            target_id=edge["target"],
            weight=edge["weight"],
            edge_type=",".join(edge.get("edge_types", ["semantic"])),
        )
        db.add(rel)

    db.commit()
    return graph.stats


def get_graph(db: Session) -> dict:
    """
    Returns the full graph for frontend visualization.
    Nodes = all memories (id, title, file_type, importance).
    Edges = persisted relationships.
    """
    memories = get_all_memories()
    nodes = [
        {
            "id":         m["id"],
            "title":      m.get("title", ""),
            "file_type":  m.get("file_type", ""),
            "importance": m.get("importance_score", 0.5),
        }
        for m in memories
    ]

    edges_orm = db.query(MemoryRelationship).all()
    edges = [e.to_dict() for e in edges_orm]

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
    }


def get_neighbors(db: Session, memory_id: int, top_k: int = 10) -> list[dict]:
    """
    Returns the top_k most strongly connected memories to a given memory.
    """
    edges = (
        db.query(MemoryRelationship)
        .filter(
            (MemoryRelationship.source_id == memory_id) |
            (MemoryRelationship.target_id == memory_id)
        )
        .order_by(MemoryRelationship.weight.desc())
        .limit(top_k)
        .all()
    )

    neighbor_ids = []
    for e in edges:
        neighbor_ids.append(
            e.target_id if e.source_id == memory_id else e.source_id
        )

    from app.models.memory import Memory
    neighbors = db.query(Memory).filter(Memory.id.in_(neighbor_ids)).all()
    return [m.to_dict() for m in neighbors]


