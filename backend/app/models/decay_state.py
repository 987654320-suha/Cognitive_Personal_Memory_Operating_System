# ðŸ“ LOCATION: backend/app/models/decay_state.py
"""
decay_state.py
===============
Persists ContextDecayModel state to SQLite so adaptive half-lives
survive server restarts.
"""

from sqlalchemy import Column, Integer, Float, String, ForeignKey
from database.database import Base


class DecayState(Base):
    __tablename__ = "decay_states"

    id                   = Column(Integer, primary_key=True, index=True)
    memory_id            = Column(Integer, ForeignKey("memories.id"), unique=True, nullable=False, index=True)
    last_reinforced      = Column(String, nullable=False)   # ISO datetime string
    reinforcement_count  = Column(Integer, default=0)
    effective_half_life  = Column(Float,   default=90.0)
    category             = Column(String,  default="default")

    def to_dict(self):
        return {
            "memory_id":            self.memory_id,
            "last_reinforced":      self.last_reinforced,
            "reinforcement_count":  self.reinforcement_count,
            "effective_half_life":  self.effective_half_life,
            "category":             self.category,
        }


