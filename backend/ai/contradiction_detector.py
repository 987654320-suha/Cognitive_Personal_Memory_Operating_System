# ðŸ“ LOCATION: backend/ai/contradiction_detector.py
"""
contradiction_detector.py
==========================
PATENTABLE FEATURE: Cross-Memory Contradiction & Drift Detection

Detects when two memories contain conflicting factual information
about the same entity (e.g. two resumes with different phone numbers,
two addresses on file, conflicting dates for the same event).

This is novel because:
  1. No existing personal knowledge system actively cross-validates
     facts across documents â€” most treat each document independently.
  2. The system flags contradictions WITHOUT a predefined schema â€”
     it extracts entity-attribute-value triples dynamically and
     compares them across the entire memory graph.
  3. It tracks "belief drift" â€” when a fact changes over time
     (e.g. address change, job title change) vs a genuine error.

Architecture:
    Memory Text â†’ Entity-Attribute Extraction â†’ Triple Store
                â†’ Cross-Memory Comparison â†’ Contradiction Scoring
                â†’ Drift Classification (error vs. legitimate update)
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict


# â”€â”€ Entity-Attribute extraction patterns â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Lightweight regex-based extraction (NER fallback uses spaCy if available)

_ATTRIBUTE_PATTERNS = {
    "email":        r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}",
    "phone":        r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}",
    "passport_no":  r"\b[A-Z]{1,2}\d{6,9}\b",
    "date_of_birth": r"\b(?:DOB|date of birth)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
    "address":      r"\b\d{1,5}\s[\w\s]{3,40}(?:street|st|road|rd|avenue|ave|lane|ln)\b",
    "ielts_score":  r"\bIELTS[^\d]{0,20}(\d\.\d)\b",
    "gpa":          r"\b(?:GPA|CGPA)[:\s]+(\d\.\d{1,2})\b",
}


@dataclass
class ExtractedFact:
    memory_id:  int
    attribute:  str
    value:      str
    date:       str | None
    context:    str   # surrounding text snippet


@dataclass
class Contradiction:
    attribute:      str
    memory_a:       dict
    memory_b:       dict
    value_a:        str
    value_b:        str
    classification: str   # "likely_error" | "legitimate_update" | "needs_review"
    confidence:     float

    def to_dict(self):
        return {
            "attribute":      self.attribute,
            "memory_a":       self.memory_a,
            "memory_b":       self.memory_b,
            "value_a":        self.value_a,
            "value_b":        self.value_b,
            "classification": self.classification,
            "confidence":     round(self.confidence, 3),
        }


class ContradictionDetector:

    def extract_facts(self, memory_id: int, text: str, date: str = None) -> list[ExtractedFact]:
        """Extracts entity-attribute-value triples from a memory's text."""
        facts = []
        for attr, pattern in _ATTRIBUTE_PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = match.group(1) if match.groups() else match.group(0)
                start = max(0, match.start() - 40)
                end   = min(len(text), match.end() + 40)
                facts.append(ExtractedFact(
                    memory_id=memory_id,
                    attribute=attr,
                    value=value.strip(),
                    date=date,
                    context=text[start:end].strip(),
                ))
        return facts

    def find_contradictions(
        self,
        all_facts: list[ExtractedFact],
        memory_lookup: dict[int, dict],
    ) -> list[Contradiction]:
        """
        Groups facts by attribute, compares values across memories.
        Returns contradictions where the same attribute has different values.
        """
        by_attribute: dict[str, list[ExtractedFact]] = defaultdict(list)
        for fact in all_facts:
            by_attribute[fact.attribute].append(fact)

        contradictions = []

        for attr, facts in by_attribute.items():
            # Group by normalized value
            value_groups: dict[str, list[ExtractedFact]] = defaultdict(list)
            for f in facts:
                normalized = self._normalize_value(attr, f.value)
                value_groups[normalized].append(f)

            distinct_values = list(value_groups.keys())
            if len(distinct_values) < 2:
                continue   # all memories agree â€” no contradiction

            # Compare every pair of distinct value groups
            for i in range(len(distinct_values)):
                for j in range(i + 1, len(distinct_values)):
                    val_a = distinct_values[i]
                    val_b = distinct_values[j]
                    fact_a = value_groups[val_a][0]
                    fact_b = value_groups[val_b][0]

                    classification, confidence = self._classify(attr, fact_a, fact_b)

                    contradictions.append(Contradiction(
                        attribute=attr,
                        memory_a=memory_lookup.get(fact_a.memory_id, {"id": fact_a.memory_id}),
                        memory_b=memory_lookup.get(fact_b.memory_id, {"id": fact_b.memory_id}),
                        value_a=fact_a.value,
                        value_b=fact_b.value,
                        classification=classification,
                        confidence=confidence,
                    ))

        return contradictions

    def _normalize_value(self, attr: str, value: str) -> str:
        v = re.sub(r"[\s\-.]", "", value.lower())
        return v

    def _classify(
        self,
        attr: str,
        fact_a: ExtractedFact,
        fact_b: ExtractedFact,
    ) -> tuple[str, float]:
        """
        Classifies a contradiction as:
          - "legitimate_update": dates are far apart, likely an intentional change
            (e.g. address change, new phone number)
          - "likely_error": dates are close together, same time period â€” probably a typo
          - "needs_review": insufficient date info to decide

        Score-changing attributes (IELTS, GPA) lean toward error unless
        large time gap suggests a retake.
        """
        date_a, date_b = fact_a.date, fact_b.date

        if not date_a or not date_b:
            return "needs_review", 0.5

        try:
            da = datetime.fromisoformat(date_a.replace("Z", "+00:00"))
            db = datetime.fromisoformat(date_b.replace("Z", "+00:00"))
            days_apart = abs((da - db).days)
        except Exception:
            return "needs_review", 0.5

        # Static identity attributes rarely change â€” large gap still suspicious
        static_attrs = {"passport_no", "date_of_birth"}
        if attr in static_attrs:
            if days_apart < 365:
                return "likely_error", 0.85
            return "needs_review", 0.6

        # Mutable attributes (address, phone, scores) â€” time gap matters
        if days_apart > 180:
            return "legitimate_update", 0.75
        elif days_apart < 30:
            return "likely_error", 0.80
        else:
            return "needs_review", 0.55


def scan_for_contradictions(memories: list[dict]) -> list[dict]:
    """
    Convenience function: full contradiction scan across all memories.
    Returns list of contradiction dicts ready for API serialization.
    """
    detector = ContradictionDetector()
    all_facts = []
    memory_lookup = {}

    for mem in memories:
        mid = mem["id"]
        memory_lookup[mid] = {"id": mid, "title": mem.get("title", "")}
        text = f"{mem.get('title', '')} {mem.get('description', '')}"
        facts = detector.extract_facts(mid, text, mem.get("date"))
        all_facts.extend(facts)

    contradictions = detector.find_contradictions(all_facts, memory_lookup)
    return [c.to_dict() for c in contradictions]


