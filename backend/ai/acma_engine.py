# ðŸ“ LOCATION: backend/ai/acma_engine.py
"""
acma_engine.py  â€” ACCURACY FIX v2
====================================
ROOT CAUSE FIXES:
  1. Semantic weight raised from 0.35 â†’ 0.55 â€” the embedding + BM25 hybrid
     score is now the dominant signal (was being diluted too much by other factors
     which hurt precision on simple queries like "resume").
  2. Hybrid score (from hybrid_search RRF) replaces raw FAISS cosine as the
     semantic component â€” much more accurate.
  3. Title/filename exact match is now a HARD BOOST â€” if the query appears
     in the filename, that memory gets a +0.3 activation bonus regardless
     of other scores. This is the fix for "I searched resume but got car photo".
  4. Importance weight reduced from 0.10 â†’ 0.05 â€” was causing high-importance
     low-relevance docs to outrank low-importance high-relevance ones.
  5. Goal weight reduced from 0.25 â†’ 0.15 when no goals are active to prevent
     goal-bias from polluting unrelated queries.
"""

from __future__ import annotations
import math
import json
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone

DEFAULT_WEIGHTS = {
    "semantic":      0.55,   # FIX: raised from 0.35
    "goal":          0.15,   # FIX: reduced from 0.25
    "relationship":  0.10,   # FIX: reduced from 0.15
    "importance":    0.05,   # FIX: reduced from 0.10
    "temporal":      0.10,
    "access":        0.05,
}

# Hard boost constants
EXACT_TITLE_BOOST    = 0.30   # query word in filename/title
PARTIAL_TITLE_BOOST  = 0.15   # query partially in title


@dataclass
class MemoryActivation:
    memory_id: int
    title:       str
    description: str
    source:      str
    image:       Optional[str]
    date:        Optional[str]
    location:    Optional[str]
    objects:     list
    file_type:   str = ""
    text_content: str = ""
    user_id:     Optional[int] = None

    semantic_score:     float = 0.0
    goal_score:         float = 0.0
    relationship_score: float = 0.0
    importance_score:   float = 0.0
    temporal_score:     float = 0.0
    access_score:       float = 0.0
    title_boost:        float = 0.0

    activation_score:   float = 0.0
    matched_goals:      list  = field(default_factory=list)
    activation_reason:  str   = ""

    def to_dict(self):
        return {
            "id":               self.memory_id,
            "user_id":          self.user_id,
            "title":            self.title,
            "description":      self.description,
            "source":           self.source,
            "image":            self.image,
            "date":             self.date,
            "text_content":     self.text_content,
            "location":         self.location,
            "objects":          self.objects,
            "file_type":        self.file_type,
            "activation_score": round(self.activation_score, 4),
            "components": {
                "semantic":     round(self.semantic_score, 4),
                "goal":         round(self.goal_score, 4),
                "relationship": round(self.relationship_score, 4),
                "importance":   round(self.importance_score, 4),
                "temporal":     round(self.temporal_score, 4),
                "access":       round(self.access_score, 4),
                "title_boost":  round(self.title_boost, 4),
            },
            "matched_goals":     self.matched_goals,
            "activation_reason": self.activation_reason,
        }


class ACMAEngine:

    def __init__(self, weights: dict = None):
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self._normalize_weights()

    def _normalize_weights(self):
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

    def rank(
        self,
        query:           str,
        hybrid_results:  list[dict] = None,          # from hybrid_search()
        all_memories:    list[dict] = None,
        active_goals:    list[dict] = None,
        goal_memory_map: dict[int, list[int]] = None,
        weights:         dict = None,
        faiss_results:   list[dict] = None,          # backward-compatibility alias
    ) -> list[MemoryActivation]:

        if hybrid_results is None and faiss_results is not None:
            hybrid_results = faiss_results
        hybrid_results = hybrid_results or []
        all_memories = all_memories or []
        active_goals = active_goals or []
        goal_memory_map = goal_memory_map or {}

        w = weights or self.weights
        mem_by_id = {m["id"]: m for m in all_memories}

        # Goal relevance map
        mem_goals: dict[int, list[str]] = {}
        goal_id_to_name = {g["id"]: g.get("name", "") for g in active_goals}
        for goal_id, mem_ids in goal_memory_map.items():
            for mid in mem_ids:
                mem_goals.setdefault(mid, []).append(goal_id_to_name.get(goal_id, ""))

        # Relationship strength
        rel_strength = self._compute_relationship_strength(all_memories)

        # Max hybrid score for normalization
        max_hybrid = max((r.get("score", 0) for r in hybrid_results), default=1.0) or 1.0

        activations = []
        for result in hybrid_results:
            mid = result.get("id") or result.get("memory_id")
            if mid is None:
                continue
            mem = mem_by_id.get(mid, result)

            # Semantic: normalized hybrid RRF score
            sem = min(result.get("score", 0) / max_hybrid, 1.0)

            # FIX: Hard title/filename boost
            title_boost = self._title_boost(query, mem)

            goal = self._goal_relevance(mid, active_goals, mem_goals)
            rel  = rel_strength.get(mid, 0.0)
            imp  = self._importance(mem)
            temp = self._temporal_relevance(mem)
            acc  = self._access_score(mem)

            # â”€â”€ ACTIVATION SCORE CALCULATION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # This is where the activation score is calculated
            activation = (
                w["semantic"]      * sem  +
                w["goal"]          * goal +
                w["relationship"]  * rel  +
                w["importance"]    * imp  +
                w["temporal"]      * temp +
                w["access"]        * acc
            )
            
            # Add title_boost directly to activation
            activation += title_boost
            
            # Ensure score doesn't exceed 1.0
            score = min(activation, 1.0)

            reason = self._build_reason(sem, goal, rel, imp, temp, acc, title_boost, mem)

            objects = mem.get("objects", [])
            if isinstance(objects, str):
                try:
                    objects = json.loads(objects)
                except Exception:
                    objects = []

            activations.append(MemoryActivation(
                memory_id=mid,
                user_id=mem.get("user_id"),
                title=mem.get("title", ""),
                description=mem.get("description", ""),
                source=mem.get("source", ""),
                image=mem.get("image"),
                date=mem.get("date"),
                location=mem.get("location"),
                objects=objects,
                file_type=mem.get("file_type", ""),
                text_content=mem.get("text_content", ""),
                semantic_score=sem,
                goal_score=goal,
                relationship_score=rel,
                importance_score=imp,
                temporal_score=temp,
                access_score=acc,
                title_boost=title_boost,  # Include title_boost in components
                activation_score=score,
                matched_goals=mem_goals.get(mid, []),
                activation_reason=reason,
            ))

        activations.sort(key=lambda a: a.activation_score, reverse=True)
        return activations

    # â”€â”€ Component calculators â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _title_boost(self, query: str, mem: dict) -> float:
        """
        FIX: Hard boost if query appears in filename or title.
        This is the PRIMARY fix for the 'resume search returns car photo' bug.
        """
        q        = query.lower().strip()
        title    = (mem.get("title") or "").lower()
        source   = (mem.get("source") or "").lower()

        # Query is IN the filename or title (e.g. "resume" in "resume_2024.pdf")
        if q in source or q in title:
            return EXACT_TITLE_BOOST

        # All meaningful words of query appear in title/source
        words = [w for w in q.split() if len(w) > 2]
        if words and all(w in title or w in source for w in words):
            return PARTIAL_TITLE_BOOST

        # Any single meaningful word matches
        if any(w in title or w in source for w in words if len(w) > 3):
            return PARTIAL_TITLE_BOOST * 0.5

        return 0.0

    def _goal_relevance(self, memory_id: int, active_goals: list, mem_goals: dict) -> float:
        if not active_goals:
            return 0.0
        linked = mem_goals.get(memory_id, [])
        if not linked:
            return 0.0
        return min(len(linked) / max(len(active_goals), 1), 1.0)

    def _compute_relationship_strength(self, all_memories: list[dict]) -> dict[int, float]:
        from collections import defaultdict
        edges: dict[int, float] = defaultdict(float)
        obj_to_mems: dict[str, list[int]] = defaultdict(list)
        for mem in all_memories:
            mid  = mem.get("id")
            objs = mem.get("objects", [])
            if isinstance(objs, str):
                try:
                    objs = json.loads(objs)
                except Exception:
                    objs = []
            for obj in objs:
                obj_to_mems[str(obj).lower()].append(mid)
        for obj, mids in obj_to_mems.items():
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    edges[mids[i]] += 1.0
                    edges[mids[j]] += 1.0
        max_s = max(edges.values(), default=1.0) or 1.0
        return {mid: s / max_s for mid, s in edges.items()}

    def _importance(self, mem: dict) -> float:
        stored = mem.get("importance_score")
        if stored is not None:
            try:
                return float(stored)
            except Exception:
                pass
        desc_len = len(mem.get("description") or "")
        has_image = 1 if mem.get("image") else 0
        return min((desc_len / 500) * 0.7 + has_image * 0.3, 1.0)

    def _temporal_relevance(self, mem: dict) -> float:
        date_str = mem.get("date") or mem.get("created_at")
        if not date_str:
            return 0.3
        try:
            mem_date = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
            now      = datetime.now(timezone.utc)
            days     = (now - mem_date).days
            lam      = math.log(2) / 90
            return math.exp(-lam * max(days, 0))
        except Exception:
            return 0.3

    def _access_score(self, mem: dict) -> float:
        count = mem.get("access_count", 0) or 0
        return 1.0 - 1.0 / (1.0 + math.log1p(count))

    def _build_reason(self, sem, goal, rel, imp, temp, acc, boost, mem) -> str:
        parts = []
        if boost >= EXACT_TITLE_BOOST:
            parts.append(f"exact match in filename '{mem.get('source', '')}'")
        elif boost > 0:
            parts.append("title/filename match")
        if sem > 0.6:
            parts.append("strong semantic match")
        elif sem > 0.3:
            parts.append("moderate semantic match")
        if goal > 0.4:
            parts.append("linked to your active goal")
        if rel > 0.5:
            parts.append("frequently co-retrieved with related memories")
        if temp > 0.7:
            parts.append("recently added")
        if acc > 0.5:
            parts.append("frequently accessed")
        return "; ".join(parts) if parts else "matched by semantic similarity"


