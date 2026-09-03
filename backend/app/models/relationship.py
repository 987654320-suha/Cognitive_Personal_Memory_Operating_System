# ðŸ“ LOCATION: backend/app/models/relationship.py
"""
relationship.py
===============
SQLAlchemy model for Memory-to-Memory relationship edges.
Persists the graph built by graph_builder.py to SQLite
so it doesn't need to be recomputed on every request.
"""

from sqlalchemy import Column, Integer, Float, String, ForeignKey, UniqueConstraint
from database.database import Base


class MemoryRelationship(Base):
    __tablename__ = "memory_relationships"

    id           = Column(Integer, primary_key=True, index=True)
    source_id    = Column(Integer, ForeignKey("memories.id"), nullable=False, index=True)
    target_id    = Column(Integer, ForeignKey("memories.id"), nullable=False, index=True)
    weight       = Column(Float,  default=0.0)
    edge_type    = Column(String, default="semantic")  # semantic | object | temporal | combined

    __table_args__ = (
        UniqueConstraint("source_id", "target_id", name="uq_memory_relationship"),
    )

    def to_dict(self):
        return {
            "id":        self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "weight":    self.weight,
            "edge_type": self.edge_type,
        }


