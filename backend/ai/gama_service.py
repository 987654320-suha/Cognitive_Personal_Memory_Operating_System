"""
GAMA â€” Goal-Aware Memory Activation
=====================================
Builds and queries the Goal Graph: a many-to-many graph where
goals are nodes and memories are edges annotated with relevance weight.

Architecture:
    Goal â”€â”€(weight)â”€â”€â–º Memory â”€â”€(weight)â”€â”€â–º Goal
    Goals can be parent/child (Germany Masters â†’ University Research).

This module plugs into the existing memory pipeline without touching
the FAISS or embedding services.
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.orm import Session


# â”€â”€â”€ Domain models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class GoalNode:
    id: int
    name: str
    description: str
    parent_id: Optional[int] = None
    progress: float = 0.0          # 0.0 â€“ 1.0
    status: str = "active"         # active | completed | paused
    linked_memory_ids: list[int] = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parent_id": self.parent_id,
            "progress": round(self.progress, 3),
            "status": self.status,
            "linked_memory_ids": self.linked_memory_ids,
        }


@dataclass
class GoalProgressReport:
    goal: GoalNode
    total_memories: int
    present_memories: list[dict]
    missing_hints: list[str]       # inferred gaps from LLM
    completion_pct: float

    def to_dict(self):
        return {
            "goal": self.goal.to_dict(),
            "total_memories": self.total_memories,
            "present": self.present_memories,
            "missing_hints": self.missing_hints,
            "completion_pct": round(self.completion_pct, 1),
        }


# â”€â”€â”€ Goal Detector â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Keyword patterns â†’ goal categories
_GOAL_PATTERNS = [
    (r"\b(germany|masters|ms |msc|gre|ielts|aps|blocked account|uni application)\b", "Germany Masters"),
    (r"\b(resume|cv|cover letter|job|internship|placement|career)\b",               "Career"),
    (r"\b(certificate|udemy|coursera|edx|completion|course)\b",                     "Certifications"),
    (r"\b(project|github|portfolio|hackathon|build|develop)\b",                     "Projects"),
    (r"\b(passport|visa|travel|ticket|booking)\b",                                  "Travel / Visa"),
    (r"\b(bank|finance|expense|budget|invoice|tax)\b",                              "Finance"),
    (r"\b(health|medical|hospital|doctor|prescription)\b",                          "Health"),
]


def detect_goals_from_text(text: str) -> list[str]:
    """
    Fast regex-based goal detection. Used during ingest to avoid
    an LLM call on every file. The LLM goal_detector handles ambiguous cases.
    """
    text_lower = text.lower()
    matched = []
    for pattern, goal_name in _GOAL_PATTERNS:
        if re.search(pattern, text_lower):
            matched.append(goal_name)
    return list(dict.fromkeys(matched))  # preserve order, dedupe


# â”€â”€â”€ GAMA Service â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class GAMAService:
    """
    Manages the Goal Graph stored in the existing SQLite DB.
    Depends on Goal and GoalMemory SQLAlchemy models.

    Usage:
        svc = GAMAService(db_session)
        svc.link_memory_to_goals(memory_id, text_content)
        report = svc.get_progress_report(goal_id)
    """

    def __init__(self, db: Session):
        self.db = db

    # â”€â”€ Core graph operations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def ensure_goal_exists(self, name: str, description: str = "", parent_id: int = None):
        """
        Idempotent: get or create a goal node.
        Returns the Goal ORM object.
        """
        from app.models.goal import Goal
        existing = self.db.query(Goal).filter(Goal.name == name).first()
        if existing:
            return existing
        goal = Goal(name=name, description=description, parent_id=parent_id, status="active")
        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)
        return goal

    def link_memory_to_goals(self, memory_id: int, text_content: str, extra_goals: list[str] = None):
        """
        Detect goals from text, then create GoalMemory edges.
        Called from memory_pipeline.py after a file is ingested.
        """
        from app.models.goal_memory import GoalMemory

        detected = detect_goals_from_text(text_content)
        if extra_goals:
            detected = list(dict.fromkeys(detected + extra_goals))

        for goal_name in detected:
            goal = self.ensure_goal_exists(goal_name)
            # Avoid duplicate edges
            exists = (
                self.db.query(GoalMemory)
                .filter(GoalMemory.goal_id == goal.id, GoalMemory.memory_id == memory_id)
                .first()
            )
            if not exists:
                edge = GoalMemory(goal_id=goal.id, memory_id=memory_id, relevance_weight=1.0)
                self.db.add(edge)

        self.db.commit()
        return detected

    def get_goal_memory_map(self) -> dict[int, list[int]]:
        """
        Returns {goal_id: [memory_id, ...]} for the full graph.
        Used by ACMAEngine.rank().
        """
        from app.models.goal_memory import GoalMemory
        rows = self.db.query(GoalMemory).all()
        result: dict[int, list[int]] = {}
        for row in rows:
            result.setdefault(row.goal_id, []).append(row.memory_id)
        return result

    def get_active_goals(self) -> list[dict]:
        from app.models.goal import Goal
        goals = self.db.query(Goal).filter(Goal.status == "active").all()
        return [
            {"id": g.id, "name": g.name, "description": g.description or ""}
            for g in goals
        ]

    # â”€â”€ Progress engine â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def get_progress_report(self, goal_id: int) -> GoalProgressReport:
        """
        Computes goal completion by checking which expected document types
        are present in linked memories.
        """
        from app.models.goal import Goal
        from app.models.goal_memory import GoalMemory
        from app.models.memory import Memory

        goal_orm = self.db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal_orm:
            raise ValueError(f"Goal {goal_id} not found")

        links = self.db.query(GoalMemory).filter(GoalMemory.goal_id == goal_id).all()
        memory_ids = [lnk.memory_id for lnk in links]
        memories = self.db.query(Memory).filter(Memory.id.in_(memory_ids)).all() if memory_ids else []

        goal_node = GoalNode(
            id=goal_orm.id,
            name=goal_orm.name,
            description=goal_orm.description or "",
            parent_id=goal_orm.parent_id,
            status=goal_orm.status or "active",
            linked_memory_ids=memory_ids,
        )

        present = [
            {"id": m.id, "title": m.title, "date": m.date, "image": m.image}
            for m in memories
        ]

        # Infer what might be missing based on goal name
        missing = self._infer_missing_documents(goal_node.name, [m.title or "" for m in memories])
        completion = min(len(present) / max(len(present) + len(missing), 1), 1.0) * 100

        return GoalProgressReport(
            goal=goal_node,
            total_memories=len(memories),
            present_memories=present,
            missing_hints=missing,
            completion_pct=completion,
        )

    def _infer_missing_documents(self, goal_name: str, present_titles: list[str]) -> list[str]:
        """
        Rule-based gap detection. Patent contribution: automatic checklist
        inference from goal context without requiring user to define requirements.
        """
        checklist_by_goal = {
            "Germany Masters": [
                "IELTS certificate", "Resume / CV", "Passport copy",
                "APS certificate", "Blocked account proof", "Motivation letter",
                "Bachelor's degree certificate", "Transcripts",
            ],
            "Career": ["Resume / CV", "Cover letter", "LinkedIn export", "References"],
            "Certifications": [],   # dynamic â€” hard to predict
            "Travel / Visa": ["Passport", "Visa application", "Ticket booking", "Hotel booking"],
            "Finance": ["Bank statement", "Tax return", "Salary slip"],
        }
        expected = checklist_by_goal.get(goal_name, [])
        present_lower = {t.lower() for t in present_titles}
        missing = []
        for item in expected:
            if not any(word in present_lower for word in item.lower().split()[:2]):
                missing.append(item)
        return missing


