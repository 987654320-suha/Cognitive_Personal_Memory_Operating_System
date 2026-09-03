"""
app/models/memory_history.py
============================
MemoryHistory â€” Stores previous versions of a memory whenever it is updated.

This enables:
  - Temporal experiment: verify CogniSphere returns the LATEST version
  - Update experiment: confirm old versions are preserved + traceable
  - Contradiction history: track when conflicting facts were introduced
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.sql import func
from database.database import Base


class MemoryHistory(Base):
    __tablename__ = "memory_history"

    id               = Column(Integer, primary_key=True, index=True)
    memory_id        = Column(Integer, index=True, nullable=False)  # FK to memories.id
    version          = Column(Integer, nullable=False)              # Which version this snapshot is
    title            = Column(String)
    description      = Column(Text)
    importance_score = Column(Float, default=0.5)
    source           = Column(String)
    file_type        = Column(String)
    date             = Column(String)                               # Original date of this memory version
    archived_at      = Column(String)                              # ISO string when this version was archived
    change_reason    = Column(String, default="manual_update")     # "manual_update" | "contradiction_resolved"

    def to_dict(self):
        return {
            "id":               self.id,
            "memory_id":        self.memory_id,
            "version":          self.version,
            "title":            self.title,
            "description":      self.description,
            "importance_score": self.importance_score or 0.5,
            "source":           self.source,
            "file_type":        self.file_type,
            "date":             self.date,
            "archived_at":      self.archived_at,
            "change_reason":    self.change_reason,
        }


