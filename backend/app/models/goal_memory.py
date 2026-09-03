"""
app/models/goal_memory.py
=========================
Edge table between Goal and Memory.
relevance_weight allows future fine-grained scoring.
"""

from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint
from database.database import Base


class GoalMemory(Base):
    __tablename__ = "goal_memories"

    id               = Column(Integer, primary_key=True, index=True)
    goal_id          = Column(Integer, ForeignKey("goals.id"),    nullable=False, index=True)
    memory_id        = Column(Integer, ForeignKey("memories.id"), nullable=False, index=True)
    relevance_weight = Column(Float, default=1.0)

    __table_args__ = (
        UniqueConstraint("goal_id", "memory_id", name="uq_goal_memory"),
    )

    def to_dict(self):
        return {
            "id":               self.id,
            "goal_id":          self.goal_id,
            "memory_id":        self.memory_id,
            "relevance_weight": self.relevance_weight,
        }


