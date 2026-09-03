# ðŸ“ LOCATION: backend/ai/graph_builder.py
"""
graph_builder.py
================
Builds a Memory Relationship Graph where nodes are memories and
weighted edges represent semantic + object co-occurrence similarity.

Patent contribution: automatic graph construction without user input.
Edges are computed from:
  1. Shared detected objects (YOLO co-occurrence)
  2. Semantic embedding cosine similarity above a threshold
  3. Temporal proximity (files created/saved close in time)

The graph is used by ACMAEngine._compute_relationship_strength()
and the /graph API endpoint for frontend visualization.
"""

from __future__ import annotations
import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MemoryNode:
    id: int
    title: str
    file_type: str
    date: Optional[str]
    objects: list[str]
    goals: list[str] = field(default_factory=list)


@dataclass
class MemoryEdge:
    source_id: int
    target_id: int
    weight: float          # 0.0 â€“ 1.0
    edge_types: list[str]  # ["object", "semantic", "temporal"]

    def to_dict(self):
        return {
            "source":     self.source_id,
            "target":     self.target_id,
            "weight":     round(self.weight, 4),
            "edge_types": self.edge_types,
        }


@dataclass
class MemoryGraph:
    nodes: list[dict]
    edges: list[dict]
    stats: dict

    def to_dict(self):
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "stats": self.stats,
        }


class GraphBuilder:
    """
    Builds the Memory Relationship Graph from DB memories.

    Usage:
        builder = GraphBuilder()
        graph   = builder.build(memories)   # list[dict] from DB
    """

    def __init__(
        self,
        semantic_threshold: float = 0.65,
        temporal_window_days: int = 7,
        object_weight: float = 0.40,
        semantic_weight: float = 0.45,
        temporal_weight: float = 0.15,
    ):
        self.semantic_threshold  = semantic_threshold
        self.temporal_window     = temporal_window_days
        self.w_object   = object_weight
        self.w_semantic = semantic_weight
        self.w_temporal = temporal_weight

    def build(self, memories: list[dict]) -> MemoryGraph:
        """
        Main entry point. Accepts list of memory dicts (from DB).
        Returns a MemoryGraph ready for API serialization or ACMA.
        """
        nodes = self._build_nodes(memories)
        edges = self._build_edges(memories)

        stats = {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "avg_degree": round(
                (len(edges) * 2) / max(len(nodes), 1), 2
            ),
            "density": round(
                len(edges) / max((len(nodes) * (len(nodes) - 1)) / 2, 1), 4
            ),
        }

        return MemoryGraph(nodes=nodes, edges=edges, stats=stats)

    # â”€â”€ Node construction â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _build_nodes(self, memories: list[dict]) -> list[dict]:
        nodes = []
        for m in memories:
            nodes.append({
                "id":        m["id"],
                "title":     m.get("title", ""),
                "file_type": m.get("file_type", ""),
                "date":      m.get("date", ""),
                "objects":   self._parse_list(m.get("objects")),
                "importance": m.get("importance_score", 0.5),
            })
        return nodes

    # â”€â”€ Edge construction â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _build_edges(self, memories: list[dict]) -> list[dict]:
        n = len(memories)
        edges: list[dict] = []

        # Pre-parse embeddings and objects once
        embeddings = {}
        objects    = {}
        dates      = {}

        for m in memories:
            mid = m["id"]
            emb = m.get("embedding", [])
            embeddings[mid] = json.loads(emb) if isinstance(emb, str) else (emb or [])
            objects[mid]    = set(self._parse_list(m.get("objects")))
            dates[mid]      = m.get("date", "")

        for i in range(n):
            for j in range(i + 1, n):
                a = memories[i]
                b = memories[j]
                aid, bid = a["id"], b["id"]

                edge_types: list[str] = []
                weights:    list[float] = []

                # 1. Object co-occurrence
                obj_score = self._object_similarity(objects[aid], objects[bid])
                if obj_score > 0:
                    edge_types.append("object")
                    weights.append(self.w_object * obj_score)

                # 2. Semantic similarity
                sem_score = self._cosine(embeddings[aid], embeddings[bid])
                if sem_score >= self.semantic_threshold:
                    edge_types.append("semantic")
                    weights.append(self.w_semantic * sem_score)

                # 3. Temporal proximity
                temp_score = self._temporal_similarity(dates[aid], dates[bid])
                if temp_score > 0.5:
                    edge_types.append("temporal")
                    weights.append(self.w_temporal * temp_score)

                if edge_types:
                    total_weight = min(sum(weights), 1.0)
                    edges.append(MemoryEdge(
                        source_id=aid,
                        target_id=bid,
                        weight=total_weight,
                        edge_types=edge_types,
                    ).to_dict())

        return edges

    # â”€â”€ Similarity calculators â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _object_similarity(self, objs_a: set, objs_b: set) -> float:
        if not objs_a or not objs_b:
            return 0.0
        intersection = len(objs_a & objs_b)
        union        = len(objs_a | objs_b)
        return intersection / union  # Jaccard

    def _cosine(self, a: list, b: list) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot  = sum(x * y for x, y in zip(a, b))
        norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
        return dot / norm if norm > 0 else 0.0

    def _temporal_similarity(self, date_a: str, date_b: str) -> float:
        if not date_a or not date_b:
            return 0.0
        try:
            from datetime import datetime, timezone
            da = datetime.fromisoformat(date_a.replace("Z", "+00:00"))
            db = datetime.fromisoformat(date_b.replace("Z", "+00:00"))
            days_apart = abs((da - db).days)
            if days_apart > self.temporal_window:
                return 0.0
            return 1.0 - (days_apart / self.temporal_window)
        except Exception:
            return 0.0

    def _parse_list(self, value) -> list:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return []
        return []


# â”€â”€ Convenience function â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_memory_graph(memories: list[dict]) -> MemoryGraph:
    """One-call convenience wrapper."""
    return GraphBuilder().build(memories)


