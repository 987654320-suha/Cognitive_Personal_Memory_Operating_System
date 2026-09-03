"""
evidence_service.py
Builds explainable evidence for every retrieved memory.
"""

from __future__ import annotations


def build_evidence(memories: list[dict]) -> list[dict]:
    evidence = []

    for mem in memories:
        reasons = []

        # match reasons already computed
        reasons.extend(mem.get("match_reasons", []))

        # goals
        for goal in mem.get("matched_goals", []):
            reasons.append(f"Related Goal: {goal}")

        # access frequency
        if mem.get("access_count", 0) > 5:
            reasons.append("Frequently Accessed")

        # recency
        if mem.get("created_at"):
            reasons.append("Recent Memory")

        evidence.append({
            "id": mem.get("id"),
            "title": mem.get("title"),
            "confidence": round(
                mem.get("confidence", 90),
                1,
            ),
            "activation_score": round(
                mem.get("activation_score", 0),
                3,
            ),
            "match_reasons": reasons,
            "relationship": mem.get("relationship_type"),
            "relationship_strength": round(
                mem.get("relationship_strength", 0),
                2,
            ),
        })

    return evidence


