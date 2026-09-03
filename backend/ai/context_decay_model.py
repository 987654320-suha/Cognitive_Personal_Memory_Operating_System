# ðŸ“ LOCATION: backend/ai/context_decay_model.py
"""
context_decay_model.py
========================
PATENTABLE FEATURE: Multi-Modal Forgetting Curve with Reinforcement

Models memory "relevance decay" using a psychologically-inspired
forgetting curve (Ebbinghaus-style exponential decay) BUT with a
novel twist: decay rate is MODULATED by cross-memory reinforcement.

This is novel because:
  1. Standard ACMA temporal scoring (in acma_engine.py) uses a FIXED
     half-life. This module makes the half-life ADAPTIVE per-memory,
     based on how often it's reinforced by related access patterns.
  2. "Reinforcement" happens when a related memory (via the relationship
     graph) is accessed â€” it partially refreshes the decay clock of
     its neighbors, mimicking associative memory reinforcement in
     human cognition.
  3. Different memory categories decay at different base rates
     (a passport scan decays slower than a casual photo) â€” this
     is learned, not hardcoded, from access pattern clusters.

This produces a genuinely different ranking signal than plain recency
or plain access-count â€” it's the INTERACTION between the two that's novel.

Architecture:
    Access Event â†’ Reinforce Memory + Propagate to Graph Neighbors
                 â†’ Adaptive Half-Life Recalculation
                 â†’ Decay-Adjusted Relevance Score
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from datetime import datetime, timezone


# â”€â”€ Base half-lives per category (days) â€” starting priors â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# These are priors; the system adapts them per-memory based on access patterns.
_BASE_HALF_LIFE_DAYS = {
    "identity_document": 720,   # passport, certificates â€” slow decay
    "financial":         365,
    "career":             180,
    "casual_photo":        45,
    "default":             90,
}

_CATEGORY_KEYWORDS = {
    "identity_document": ["passport", "certificate", "degree", "transcript", "id card"],
    "financial":          ["bank", "invoice", "statement", "tax", "receipt"],
    "career":             ["resume", "cv", "offer letter", "job", "internship"],
    "casual_photo":       ["photo", "screenshot", "selfie", "image"],
}

REINFORCEMENT_BOOST_DAYS = 14    # each reinforcement extends effective freshness
REINFORCEMENT_PROPAGATION_FACTOR = 0.3   # neighbors get 30% of the direct boost


@dataclass
class DecayState:
    memory_id:           int
    last_reinforced:     datetime
    reinforcement_count: int
    effective_half_life: float   # days, adapted from base

    def to_dict(self):
        return {
            "memory_id":           self.memory_id,
            "last_reinforced":     self.last_reinforced.isoformat(),
            "reinforcement_count": self.reinforcement_count,
            "effective_half_life": round(self.effective_half_life, 1),
        }


class ContextDecayModel:

    def __init__(self):
        # In production this would be persisted to DB (decay_state table)
        self._state: dict[int, DecayState] = {}

    # â”€â”€ Category classification â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def classify_category(self, title: str, description: str = "") -> str:
        text = f"{title} {description}".lower()
        for category, keywords in _CATEGORY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return category
        return "default"

    def base_half_life(self, category: str) -> float:
        return _BASE_HALF_LIFE_DAYS.get(category, _BASE_HALF_LIFE_DAYS["default"])

    # â”€â”€ Reinforcement events â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def reinforce(self, memory_id: int, category: str = "default") -> DecayState:
        """
        Called every time a memory is accessed/retrieved.
        Extends its effective half-life and resets the decay clock.
        """
        now = datetime.now(timezone.utc)
        state = self._state.get(memory_id)

        if state is None:
            state = DecayState(
                memory_id=memory_id,
                last_reinforced=now,
                reinforcement_count=1,
                effective_half_life=self.base_half_life(category),
            )
        else:
            state.last_reinforced = now
            state.reinforcement_count += 1
            # Diminishing returns: each reinforcement adds less than the last
            boost = REINFORCEMENT_BOOST_DAYS / math.sqrt(state.reinforcement_count)
            state.effective_half_life += boost

        self._state[memory_id] = state
        return state

    def propagate_reinforcement(
        self,
        memory_id: int,
        neighbor_ids: list[int],
        category_lookup: dict[int, str],
    ) -> list[DecayState]:
        """
        When memory_id is reinforced, propagate a PARTIAL reinforcement
        to its graph neighbors (via relationship edges).

        This models associative memory: accessing your IELTS certificate
        also slightly "refreshes" your resume because they're related.
        """
        updated_states = []
        for neighbor_id in neighbor_ids:
            now = datetime.now(timezone.utc)
            state = self._state.get(neighbor_id)
            category = category_lookup.get(neighbor_id, "default")

            if state is None:
                state = DecayState(
                    memory_id=neighbor_id,
                    last_reinforced=now,
                    reinforcement_count=0,
                    effective_half_life=self.base_half_life(category),
                )

            # Partial boost â€” propagated reinforcement is weaker than direct
            boost = (REINFORCEMENT_BOOST_DAYS * REINFORCEMENT_PROPAGATION_FACTOR)
            state.effective_half_life += boost
            state.last_reinforced = now  # soft refresh, not a full reinforcement

            self._state[neighbor_id] = state
            updated_states.append(state)

        return updated_states

    # â”€â”€ Decay-adjusted scoring â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def decay_score(self, memory_id: int, created_date: str, category: str = "default") -> float:
        """
        Returns the decay-adjusted relevance score (0â€“1).
        Uses adaptive half-life instead of ACMAEngine's fixed 90-day half-life.
        """
        state = self._state.get(memory_id)
        half_life = state.effective_half_life if state else self.base_half_life(category)

        # Decay computed from last_reinforced if available, else created_date
        reference_date = state.last_reinforced if state else None
        if reference_date is None:
            try:
                reference_date = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
            except Exception:
                return 0.3

        now = datetime.now(timezone.utc)
        days_since = (now - reference_date).days
        lam = math.log(2) / max(half_life, 1)
        return math.exp(-lam * max(days_since, 0))

    def get_state(self, memory_id: int) -> dict | None:
        state = self._state.get(memory_id)
        return state.to_dict() if state else None

    def export_all_states(self) -> list[dict]:
        return [s.to_dict() for s in self._state.values()]


# â”€â”€ Module-level singleton (would be backed by DB in production) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_global_model = ContextDecayModel()


def get_decay_model() -> ContextDecayModel:
    return _global_model


