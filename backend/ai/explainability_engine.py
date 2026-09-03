# ðŸ“ LOCATION: backend/ai/explainability_engine.py
"""
explainability_engine.py
========================
Generates human-readable explanations for why memories were retrieved.

For each retrieved memory, produces:
  - A plain-English reason sentence
  - A confidence label (High / Medium / Low)
  - Component score breakdown bar chart data
  - Goal progress context

This is the XAI (Explainable AI) layer â€” a core patent contribution.
Every answer CogniSphere gives can be fully audited by the user.
"""

from __future__ import annotations
from dataclasses import dataclass


CONFIDENCE_THRESHOLDS = {
    "High":   0.70,
    "Medium": 0.40,
    "Low":    0.0,
}


@dataclass
class ExplainedMemory:
    memory_id:      int
    title:          str
    activation_score: float
    confidence:     str           # High | Medium | Low
    reason_sentence: str
    components:     dict          # {semantic: 0.8, goal: 0.6, ...}
    matched_goals:  list[str]
    missing_for_goals: list[str]  # what's still needed in those goals

    def to_dict(self):
        return {
            "memory_id":        self.memory_id,
            "title":            self.title,
            "activation_score": round(self.activation_score, 4),
            "confidence":       self.confidence,
            "reason_sentence":  self.reason_sentence,
            "components":       {k: round(v, 3) for k, v in self.components.items()},
            "matched_goals":    self.matched_goals,
            "missing_for_goals": self.missing_for_goals,
        }


class ExplainabilityEngine:

    def explain(
        self,
        acma_results: list[dict],
        goal_progress: dict[str, dict] = None,
    ) -> list[dict]:
        """
        Takes ACMA-ranked results and enriches each with full explanation.

        acma_results: output of ACMAEngine.rank() serialized as list[dict]
        goal_progress: {goal_name: progress_report_dict} for active goals
        """
        explained = []
        for result in acma_results:
            explained.append(
                self._explain_single(result, goal_progress or {}).to_dict()
            )
        return explained

    def _explain_single(
        self,
        result: dict,
        goal_progress: dict,
    ) -> ExplainedMemory:
        score      = result.get("activation_score", 0.0)
        components = result.get("components", {})
        goals      = result.get("matched_goals", [])

        confidence = self._confidence(score)
        reason     = self._build_reason(result, components, goals)
        missing    = self._missing_docs(goals, goal_progress)

        return ExplainedMemory(
            memory_id=result["id"],
            title=result.get("title", ""),
            activation_score=score,
            confidence=confidence,
            reason_sentence=reason,
            components=components,
            matched_goals=goals,
            missing_for_goals=missing,
        )

    def _confidence(self, score: float) -> str:
        for label, threshold in CONFIDENCE_THRESHOLDS.items():
            if score >= threshold:
                return label
        return "Low"

    def _build_reason(self, result: dict, components: dict, goals: list) -> str:
        parts = []

        sem = components.get("semantic", 0)
        if sem >= 0.7:
            parts.append("strongly matches your query semantically")
        elif sem >= 0.4:
            parts.append("partially matches your query")

        goal = components.get("goal", 0)
        if goal > 0 and goals:
            goal_str = ", ".join(goals[:2])
            parts.append(f"linked to your goal '{goal_str}'")

        rel = components.get("relationship", 0)
        if rel >= 0.5:
            parts.append("frequently retrieved alongside other relevant memories")

        imp = components.get("importance", 0)
        if imp >= 0.7:
            parts.append("marked as high-importance document")

        temp = components.get("temporal", 0)
        if temp >= 0.7:
            parts.append("recently added")
        elif temp <= 0.2:
            parts.append("older memory but still relevant")

        acc = components.get("access", 0)
        if acc >= 0.6:
            parts.append("frequently accessed")

        if not parts:
            return "Retrieved based on overall context match."

        sentence = "Retrieved because it " + ", and ".join(parts) + "."
        return sentence[0].upper() + sentence[1:]

    def _missing_docs(self, goals: list, goal_progress: dict) -> list[str]:
        missing = []
        for goal_name in goals:
            progress = goal_progress.get(goal_name, {})
            hints = progress.get("missing_hints", [])
            missing.extend(hints)
        return list(dict.fromkeys(missing))[:5]   # dedupe, cap at 5


def explain_results(
    acma_results: list[dict],
    goal_progress: dict = None,
) -> list[dict]:
    """One-call convenience wrapper."""
    return ExplainabilityEngine().explain(acma_results, goal_progress)


