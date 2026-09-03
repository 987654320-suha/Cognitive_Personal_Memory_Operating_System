# ðŸ“ LOCATION: backend/ai/temporal_reasoner.py
"""
temporal_reasoner.py
====================
Time-aware reasoning over memories.

Capabilities:
  1. Timeline clustering: group memories into life phases/periods
  2. Temporal query parsing: "last month", "before Germany trip", "in 2024"
  3. Recency boost: memories near a target date score higher
  4. Periodic pattern detection: recurring events (monthly bank statements etc.)

Used by search_service.py and chat_service.py to enrich queries
that contain time references.
"""

from __future__ import annotations
import re
import math
from datetime import datetime, timezone, timedelta


# â”€â”€ Temporal query patterns â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_RELATIVE_PATTERNS = [
    (r"\b(today|tonight)\b",             lambda now: (now, now)),
    (r"\b(yesterday)\b",                  lambda now: (now - timedelta(days=1),  now - timedelta(days=1))),
    (r"\b(this week)\b",                  lambda now: (now - timedelta(days=7),  now)),
    (r"\b(last week)\b",                  lambda now: (now - timedelta(days=14), now - timedelta(days=7))),
    (r"\b(this month)\b",                 lambda now: (now.replace(day=1),       now)),
    (r"\b(last month)\b",                 lambda now: (_last_month_start(now),   now.replace(day=1) - timedelta(days=1))),
    (r"\b(this year)\b",                  lambda now: (now.replace(month=1, day=1), now)),
    (r"\b(last year)\b",                  lambda now: (now.replace(year=now.year - 1, month=1, day=1),
                                                        now.replace(year=now.year - 1, month=12, day=31))),
    (r"\blast (\d+) days?\b",             None),  # handled separately
    (r"\blast (\d+) months?\b",           None),
    (r"\bin (\d{4})\b",                   None),  # year match
]


def _last_month_start(now: datetime) -> datetime:
    first = now.replace(day=1)
    return (first - timedelta(days=1)).replace(day=1)


def parse_temporal_query(query: str) -> dict | None:
    """
    Extracts a date range from a natural language query.

    Returns:
        {"start": datetime, "end": datetime, "original": str}
        or None if no temporal reference found.
    """
    now   = datetime.now(timezone.utc)
    lower = query.lower()

    for pattern, resolver in _RELATIVE_PATTERNS:
        m = re.search(pattern, lower)
        if not m:
            continue

        if resolver is not None:
            start, end = resolver(now)
            return {"start": start, "end": end, "original": m.group()}

        # Handle dynamic patterns
        groups = m.groups()
        if "days" in pattern and groups:
            n = int(groups[0])
            return {"start": now - timedelta(days=n), "end": now, "original": m.group()}
        if "months" in pattern and groups:
            n = int(groups[0])
            return {"start": now - timedelta(days=n * 30), "end": now, "original": m.group()}
        if r"\d{4}" in pattern and groups:
            year = int(groups[0])
            start = datetime(year, 1,  1,  tzinfo=timezone.utc)
            end   = datetime(year, 12, 31, tzinfo=timezone.utc)
            return {"start": start, "end": end, "original": m.group()}

    return None


def temporal_score(memory_date: str, target_date: datetime, half_life_days: int = 90) -> float:
    """
    Returns a 0â€“1 score based on how close memory_date is to target_date.
    Uses exponential decay symmetric around target.
    """
    if not memory_date:
        return 0.3
    try:
        mem_dt = datetime.fromisoformat(memory_date.replace("Z", "+00:00"))
        days_apart = abs((mem_dt - target_date).days)
        lam = math.log(2) / half_life_days
        return math.exp(-lam * days_apart)
    except Exception:
        return 0.3


def cluster_by_period(memories: list[dict], period: str = "month") -> dict[str, list[dict]]:
    """
    Groups memories by time period: 'day', 'week', 'month', 'year'.

    Returns: {"2024-06": [memory_dict, ...], ...}
    """
    clusters: dict[str, list[dict]] = {}

    for mem in memories:
        date_str = mem.get("date", "")
        if not date_str:
            key = "unknown"
        else:
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if period == "day":
                    key = dt.strftime("%Y-%m-%d")
                elif period == "week":
                    key = f"{dt.year}-W{dt.strftime('%W')}"
                elif period == "month":
                    key = dt.strftime("%Y-%m")
                elif period == "year":
                    key = str(dt.year)
                else:
                    key = dt.strftime("%Y-%m")
            except Exception:
                key = "unknown"

        clusters.setdefault(key, []).append(mem)

    # Sort keys chronologically
    return dict(sorted(clusters.items()))


def detect_recurring_patterns(memories: list[dict]) -> list[dict]:
    """
    Detects memories that appear to be recurring (e.g. monthly bank statements).
    Groups by title similarity and checks if dates are evenly spaced.

    Returns list of pattern dicts:
        {"title_pattern": str, "frequency_days": int, "count": int, "memory_ids": [int]}
    """
    from collections import defaultdict
    import re as re_mod

    # Group by normalized title
    title_groups: dict[str, list[dict]] = defaultdict(list)
    for mem in memories:
        title = mem.get("title", "").lower()
        # Normalize: remove dates, numbers
        normalized = re_mod.sub(r"\d+", "", title).strip()
        normalized = re_mod.sub(r"\s+", " ", normalized)
        if len(normalized) > 3:
            title_groups[normalized].append(mem)

    patterns = []
    for norm_title, group in title_groups.items():
        if len(group) < 3:  # need at least 3 occurrences
            continue

        dates = []
        for mem in group:
            try:
                dt = datetime.fromisoformat((mem.get("date") or "").replace("Z", "+00:00"))
                dates.append(dt)
            except Exception:
                pass

        if len(dates) < 3:
            continue

        dates.sort()
        gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates) - 1)]
        avg_gap = sum(gaps) / len(gaps)
        variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)

        # Low variance = regular recurring pattern
        if variance < (avg_gap * 0.5) ** 2:
            patterns.append({
                "title_pattern":  norm_title,
                "frequency_days": round(avg_gap),
                "count":          len(group),
                "memory_ids":     [m["id"] for m in group],
            })

    return patterns


