# ðŸ“ LOCATION: backend/ai/embedding_service.py
"""
embedding_service.py  â€” ACCURACY FIX v2
========================================
ROOT CAUSE FIXES:
  1. Upgraded model: all-MiniLM-L6-v2 (384-dim) â†’ all-mpnet-base-v2 (768-dim)
     mpnet has significantly better semantic accuracy for document retrieval.
  2. Added query expansion: short queries like "resume" are expanded with
     synonyms so the embedding captures the full intent.
  3. Added text preprocessing: removes noise (special chars, extra whitespace)
     before encoding so vectors are cleaner.
  4. Caching: model loaded once at startup, not per-request.
"""

from __future__ import annotations
import os
import re
from functools import lru_cache
from threading import Lock
from typing import List, Optional

_model = None
_model_lock = Lock()
# Default to all-MiniLM-L6-v2 (384-dim, ~80 MB) to fit comfortably within Render's 512 MiB limit
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Query synonym expansion â€” improves recall for short/ambiguous queries
QUERY_EXPANSIONS: dict[str, list[str]] = {
    "resume":       ["resume", "cv", "curriculum vitae", "job application", "work experience"],
    "cv":           ["cv", "curriculum vitae", "resume", "work history"],
    "certificate":  ["certificate", "certification", "diploma", "completion", "award"],
    "ielts":        ["ielts", "english test", "language proficiency", "band score"],
    "passport":     ["passport", "travel document", "identity", "visa"],
    "bank":         ["bank statement", "account", "transaction", "finance"],
    "photo":        ["photo", "image", "picture", "photograph"],
    "invoice":      ["invoice", "bill", "receipt", "payment"],
    "degree":       ["degree", "bachelor", "master", "university", "graduation"],
    "transcript":   ["transcript", "marksheet", "grades", "academic record"],
}


@lru_cache(maxsize=1)
def _load_model() -> Optional[object]:
    """
    Load the embedding model with caching.
    Returns None if no model can be loaded.
    """
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(MODEL_NAME, device="cpu")
        dim = getattr(model, "get_sentence_embedding_dimension", lambda: "unknown")()
        print(f"[Embedding] Model loaded on-demand: {MODEL_NAME} ({dim}-dim, CPU-optimized)")
        return model
    except ImportError:
        print("[Embedding] sentence-transformers not installed. Run: pip install sentence-transformers")
        return None
    except Exception as e:
        print(f"[Embedding] Failed to load {MODEL_NAME}: {e}")
        if MODEL_NAME != "all-MiniLM-L6-v2":
            # Fallback to lightweight MiniLM if primary model fails/OOMs
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
                print(f"[Embedding] Fallback model loaded: all-MiniLM-L6-v2 (384-dim, low-memory)")
                return model
            except Exception as fallback_error:
                print(f"[Embedding] Could not load fallback model: {fallback_error}")
                return None
        return None


def _get_model() -> Optional[object]:
    """Thread-safe model getter with lazy loading."""
    global _model
    
    if _model is None:
        with _model_lock:
            if _model is None:  # Double-check locking
                _model = _load_model()
    
    return _model


def _preprocess(text: str) -> str:
    """Clean text before embedding â€” removes noise that hurts vector quality."""
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove non-printable characters
    text = re.sub(r"[^\x20-\x7E\u00C0-\u024F\u0900-\u097F]", " ", text)
    # Remove repeated punctuation
    text = re.sub(r"[.\-_/\\]{3,}", " ", text)
    return text.strip()


def expand_query(query: str) -> str:
    """
    Expands short queries with synonyms to improve recall.
    e.g. "resume" â†’ "resume cv curriculum vitae job application work experience"
    """
    q_lower = query.lower().strip()
    expansions = []
    for keyword, synonyms in QUERY_EXPANSIONS.items():
        if keyword in q_lower:
            expansions.extend(synonyms)
    if expansions:
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for s in [query] + expansions:
            if s.lower() not in seen:
                seen.add(s.lower())
                unique.append(s)
        return " ".join(unique)
    return query


def get_embedding(text: str, is_query: bool = False) -> List[float]:
    """
    Returns a high-quality embedding vector.
    is_query=True applies query expansion for better recall.
    """
    if not text or not text.strip():
        return []

    model = _get_model()
    if model is None:
        return []

    try:
        processed = _preprocess(text)
        if is_query:
            processed = expand_query(processed)

        # Truncate to model max length (prevents silent truncation artifacts)
        processed = processed[:4096]

        vector = model.encode(
            processed,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return vector.tolist()
    except Exception as e:
        print(f"[Embedding] Error: {e}")
        return []


def get_query_embedding(query: str) -> List[float]:
    """Dedicated query embedding with expansion enabled."""
    return get_embedding(query, is_query=True)


def preload_model():
    """
    Legacy startup hook — now a safe no-op.
    Models are strictly lazy-loaded on first embedding request to prevent OOM on memory-constrained servers.
    """
    pass


