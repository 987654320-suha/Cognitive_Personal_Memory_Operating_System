"""
importance_scorer.py
====================
Assigns an importance score (0.0â€“1.0) to a memory at ingest time.
Stored in the DB so ACMA can use it without recomputing.

Scoring combines:
  - Text length signal (longer = more content = more important)
  - Keyword signal (high-value document keywords)
  - File type signal
  - Title quality signal
"""

from __future__ import annotations
import re

# High-value keywords â†’ boost importance
_HIGH_VALUE_KEYWORDS = [
    r"\b(certificate|degree|diploma|transcript)\b",
    r"\b(passport|visa|id card|aadhaar|pan card)\b",
    r"\b(resume|cv|curriculum vitae)\b",
    r"\b(offer letter|appointment|contract|agreement)\b",
    r"\b(bank statement|invoice|receipt|tax)\b",
    r"\b(research|patent|publication|paper)\b",
    r"\b(ielts|gre|toefl|gmat|sat)\b",
]

_LOW_VALUE_KEYWORDS = [
    r"\b(meme|screenshot|wallpaper|icon|thumbnail)\b",
    r"\b(temp|tmp|draft|copy|backup)\b",
]


def score_importance(title: str, text: str) -> float:
    """Returns float 0.0 â€“ 1.0."""
    score = 0.0
    combined = f"{title} {text}".lower()

    # Text length (max contribution 0.3)
    text_len = len(text or "")
    score += min(text_len / 2000, 1.0) * 0.30

    # High-value keyword hits (max contribution 0.50)
    hits = sum(1 for p in _HIGH_VALUE_KEYWORDS if re.search(p, combined))
    score += min(hits * 0.25, 0.50)

    # Low-value keyword penalty (max -0.20)
    penalties = sum(1 for p in _LOW_VALUE_KEYWORDS if re.search(p, combined))
    score -= min(penalties * 0.10, 0.20)

    # Title quality: non-generic title = small boost
    generic = {"untitled", "image", "photo", "file", "document", "screenshot"}
    if title.strip().lower() not in generic and len(title.strip()) > 3:
        score += 0.10

    # Clamp
    return round(min(max(score, 0.0), 1.0), 4)


