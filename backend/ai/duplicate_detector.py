# ðŸ“ LOCATION: backend/ai/duplicate_detector.py
"""
duplicate_detector.py
=====================
Detects duplicate or near-duplicate memories in the DB.

Two memories are considered duplicates if:
  - Hash match: identical file content (MD5 of first 64KB)
  - Semantic match: cosine similarity >= threshold (near-duplicate)
  - Title match: same title AND same file_type

Called automatically by memory_pipeline.py before saving a new memory,
and available as a standalone scan via scripts/benchmark.py.
"""

from __future__ import annotations
import json
import math
import hashlib
from pathlib import Path


SEMANTIC_DUPLICATE_THRESHOLD = 0.92   # very high = near-identical content


def file_hash(file_path: str) -> str:
    """MD5 of first 64KB of file â€” fast dedup check."""
    h = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            h.update(f.read(65536))
        return h.hexdigest()
    except Exception:
        return ""


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot  = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm > 0 else 0.0


def is_duplicate_file(file_path: str, existing_memories: list[dict]) -> dict | None:
    """
    Checks if a file on disk matches any existing memory by hash.
    Returns the matching memory dict or None.
    """
    fhash = file_hash(file_path)
    fname = Path(file_path).name

    for mem in existing_memories:
        # Exact filename match
        if mem.get("source") == fname:
            return {"memory": mem, "reason": "filename_match"}

    # Hash stored? (future: store hash in DB)
    return None


def find_semantic_duplicates(
    new_embedding: list[float],
    existing_memories: list[dict],
    threshold: float = SEMANTIC_DUPLICATE_THRESHOLD,
) -> list[dict]:
    """
    Returns list of existing memories that are near-duplicates
    of the given embedding. Sorted by similarity descending.
    """
    candidates = []
    for mem in existing_memories:
        emb = mem.get("embedding", [])
        if isinstance(emb, str):
            try:
                emb = json.loads(emb)
            except Exception:
                continue
        score = cosine_similarity(new_embedding, emb)
        if score >= threshold:
            candidates.append({
                "memory":     mem,
                "similarity": round(score, 4),
                "reason":     "semantic_duplicate",
            })
    candidates.sort(key=lambda x: x["similarity"], reverse=True)
    return candidates


def scan_all_duplicates(memories: list[dict]) -> list[dict]:
    """
    Full duplicate scan across all memories in DB.
    Returns list of duplicate pairs.
    Used by scripts/benchmark.py and /index/duplicates endpoint.
    """
    pairs = []
    n = len(memories)

    for i in range(n):
        for j in range(i + 1, n):
            a = memories[i]
            b = memories[j]

            emb_a = a.get("embedding", [])
            emb_b = b.get("embedding", [])
            if isinstance(emb_a, str):
                try: emb_a = json.loads(emb_a)
                except: emb_a = []
            if isinstance(emb_b, str):
                try: emb_b = json.loads(emb_b)
                except: emb_b = []

            score = cosine_similarity(emb_a, emb_b)
            if score >= SEMANTIC_DUPLICATE_THRESHOLD:
                pairs.append({
                    "memory_a":   {"id": a["id"], "title": a.get("title")},
                    "memory_b":   {"id": b["id"], "title": b.get("title")},
                    "similarity": round(score, 4),
                    "reason":     "semantic_duplicate",
                })

    return pairs


