# ðŸ“ LOCATION: backend/app/services/contradiction_service.py
"""
contradiction_service.py
==========================
Service layer for the Contradiction Detector.
Runs the scan against live DB data and persists flagged contradictions.
"""

from __future__ import annotations
from sqlalchemy.orm import Session

from ai.contradiction_detector import scan_for_contradictions
from app.services.database_service import get_all_memories


def run_contradiction_scan(db: Session) -> dict:
    """
    Full scan across all memories. Returns contradictions grouped
    by classification for easy frontend rendering.
    """
    memories = get_all_memories()
    contradictions = scan_for_contradictions(memories)

    grouped = {"likely_error": [], "legitimate_update": [], "needs_review": []}
    for c in contradictions:
        grouped.setdefault(c["classification"], []).append(c)

    return {
        "total_contradictions": len(contradictions),
        "likely_errors":        len(grouped["likely_error"]),
        "legitimate_updates":   len(grouped["legitimate_update"]),
        "needs_review":         len(grouped["needs_review"]),
        "details":              grouped,
    }


def get_contradictions_for_memory(db: Session, memory_id: int) -> list[dict]:
    """Returns contradictions involving a specific memory."""
    full_scan = run_contradiction_scan(db)
    all_items = (
        full_scan["details"]["likely_error"] +
        full_scan["details"]["legitimate_update"] +
        full_scan["details"]["needs_review"]
    )
    return [
        c for c in all_items
        if c["memory_a"].get("id") == memory_id or c["memory_b"].get("id") == memory_id
    ]


