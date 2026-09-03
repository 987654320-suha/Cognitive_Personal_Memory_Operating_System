# ðŸ“ LOCATION: backend/ai/predictive_goal_engine.py
"""
predictive_goal_engine.py
==========================
PATENTABLE FEATURE: Predictive Goal Trajectory & Next-Action Inference

Goes beyond GAMA's reactive gap detection (what's missing NOW) into
PREDICTIVE territory: given the user's historical document acquisition
pattern, predict what they will need NEXT and when.

This is novel because:
  1. It models goal completion as a TIME-SERIES process, not a static
     checklist. Each goal has a typical "document acquisition sequence"
     learned from aggregate patterns (e.g. IELTS usually comes before
     university applications, which come before visa applications).
  2. It computes "velocity" â€” the rate at which a user is closing gaps
     in a goal â€” and projects a completion date.
  3. It generates PROACTIVE recommendations ("Based on your pace, you
     should start your APS application within 2 weeks") rather than
     only describing the current state.

Architecture:
    Goal History â†’ Sequence Model â†’ Velocity Calculation
                 â†’ Trajectory Projection â†’ Next-Action Recommendation
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta


# â”€â”€ Known document acquisition sequences (prior structure for common goals) â”€â”€
# This encodes domain knowledge: typical ORDER in which documents are acquired.
# Patent angle: the system uses this as a PRIOR, then personalizes based on
# the individual user's own historical velocity â€” a hybrid prior + adaptive model.

_GOAL_SEQUENCES = {
    "Germany Masters": [
        "Bachelor's degree certificate",
        "Transcripts",
        "IELTS certificate",
        "Resume / CV",
        "Motivation letter",
        "University application",
        "APS certificate",
        "Blocked account proof",
        "Visa application",
        "Passport copy",
    ],
    "Career": [
        "Resume / CV",
        "Cover letter",
        "LinkedIn export",
        "References",
        "Job application",
        "Offer letter",
    ],
    "Travel / Visa": [
        "Passport",
        "Visa application",
        "Ticket booking",
        "Hotel booking",
    ],
}


@dataclass
class TrajectoryPoint:
    document_name: str
    acquired:      bool
    acquired_date: str | None
    expected_order: int


@dataclass
class GoalTrajectory:
    goal_name:          str
    sequence:           list[TrajectoryPoint]
    velocity_days_per_doc: float | None   # avg days between document acquisitions
    next_recommended:   str | None
    projected_completion_date: str | None
    confidence:         float

    def to_dict(self):
        return {
            "goal_name": self.goal_name,
            "sequence": [
                {
                    "document":       p.document_name,
                    "acquired":       p.acquired,
                    "acquired_date":  p.acquired_date,
                    "expected_order": p.expected_order,
                }
                for p in self.sequence
            ],
            "velocity_days_per_doc": (
                round(self.velocity_days_per_doc, 1) if self.velocity_days_per_doc else None
            ),
            "next_recommended": self.next_recommended,
            "projected_completion_date": self.projected_completion_date,
            "confidence": round(self.confidence, 3),
        }


class PredictiveGoalEngine:

    def compute_trajectory(
        self,
        goal_name: str,
        present_memories: list[dict],   # [{title, date}, ...] from GAMA progress report
    ) -> GoalTrajectory:
        """
        Main entry point. Computes the trajectory for a single goal.
        """
        expected_sequence = _GOAL_SEQUENCES.get(goal_name, [])
        if not expected_sequence:
            return self._fallback_trajectory(goal_name, present_memories)

        # Match present memories to expected sequence items (fuzzy keyword match)
        sequence_points: list[TrajectoryPoint] = []
        acquired_dates: list[datetime] = []

        for idx, doc_name in enumerate(expected_sequence):
            match = self._find_matching_memory(doc_name, present_memories)
            acquired = match is not None
            acquired_date = match.get("date") if match else None

            if acquired_date:
                try:
                    dt = datetime.fromisoformat(acquired_date.replace("Z", "+00:00"))
                    acquired_dates.append(dt)
                except Exception:
                    pass

            sequence_points.append(TrajectoryPoint(
                document_name=doc_name,
                acquired=acquired,
                acquired_date=acquired_date,
                expected_order=idx,
            ))

        velocity = self._compute_velocity(acquired_dates)
        next_doc = self._next_recommended(sequence_points)
        projected_date = self._project_completion(sequence_points, velocity)
        confidence = self._confidence(sequence_points, velocity)

        return GoalTrajectory(
            goal_name=goal_name,
            sequence=sequence_points,
            velocity_days_per_doc=velocity,
            next_recommended=next_doc,
            projected_completion_date=projected_date,
            confidence=confidence,
        )

    # â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _find_matching_memory(self, doc_name: str, memories: list[dict]) -> dict | None:
        """Fuzzy match: checks if any keyword from doc_name appears in memory title."""
        keywords = [w.lower() for w in doc_name.split() if len(w) > 3]
        for mem in memories:
            title_lower = (mem.get("title") or "").lower()
            if any(kw in title_lower for kw in keywords):
                return mem
        return None

    def _compute_velocity(self, dates: list[datetime]) -> float | None:
        """Average days between consecutive document acquisitions."""
        if len(dates) < 2:
            return None
        dates_sorted = sorted(dates)
        gaps = [
            (dates_sorted[i + 1] - dates_sorted[i]).days
            for i in range(len(dates_sorted) - 1)
        ]
        return sum(gaps) / len(gaps) if gaps else None

    def _next_recommended(self, sequence: list[TrajectoryPoint]) -> str | None:
        """First not-yet-acquired document in the expected order."""
        for point in sequence:
            if not point.acquired:
                return point.document_name
        return None   # goal fully complete

    def _project_completion(
        self,
        sequence: list[TrajectoryPoint],
        velocity: float | None,
    ) -> str | None:
        """
        Projects a completion date based on remaining documents
        and the user's historical velocity.
        """
        if velocity is None:
            return None

        remaining = sum(1 for p in sequence if not p.acquired)
        if remaining == 0:
            return None

        days_remaining = remaining * velocity
        projected = datetime.now(timezone.utc) + timedelta(days=days_remaining)
        return projected.date().isoformat()

    def _confidence(self, sequence: list[TrajectoryPoint], velocity: float | None) -> float:
        """
        Confidence in the projection â€” higher with more historical
        data points and a consistent velocity.
        """
        acquired_count = sum(1 for p in sequence if p.acquired)
        total = len(sequence)
        coverage = acquired_count / total if total else 0

        if velocity is None:
            return coverage * 0.3   # low confidence without velocity data

        return min(coverage * 0.6 + 0.4, 0.95)

    def _fallback_trajectory(self, goal_name: str, memories: list[dict]) -> GoalTrajectory:
        """For goals without a known sequence template â€” basic count-based estimate."""
        return GoalTrajectory(
            goal_name=goal_name,
            sequence=[],
            velocity_days_per_doc=None,
            next_recommended=None,
            projected_completion_date=None,
            confidence=0.1,
        )


def compute_all_trajectories(
    active_goals: list[dict],
    goal_progress_reports: dict[str, dict],
) -> list[dict]:
    """
    Convenience function: computes trajectories for all active goals.

    active_goals: [{name, ...}, ...]
    goal_progress_reports: {goal_name: progress_report_dict}
    """
    engine = PredictiveGoalEngine()
    results = []
    for goal in active_goals:
        name = goal.get("name", "")
        report = goal_progress_reports.get(name, {})
        present = report.get("present", [])
        trajectory = engine.compute_trajectory(name, present)
        results.append(trajectory.to_dict())
    return results


