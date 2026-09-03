# ðŸ“ LOCATION: backend/ai/faiss_service.py
"""
faiss_service.py  â€” ACCURACY FIX v2
=====================================
ROOT CAUSE FIXES:
  1. Uses get_query_embedding() with expansion instead of plain get_embedding()
     so "resume" query matches "CV", "curriculum vitae" etc.
  2. Uses IndexFlatIP (exact inner product) â€” no approximation errors.
  3. Stores memory ids alongside index so we never have index/memory mismatch.
  4. Returns raw scores for RRF â€” not clamped to 0-1 range prematurely.
"""

from __future__ import annotations
import json
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("[FAISS] faiss-cpu not installed. Brute-force fallback active.")

from ai.embedding_service import get_embedding, get_query_embedding

_index            = None
_indexed_memories: list[dict] = []
_id_to_pos:       dict[int, int] = {}   # memory.id â†’ position in _indexed_memories


def build_index(memories: list[dict]) -> None:
    global _index, _indexed_memories, _id_to_pos

    vectors       = []
    valid_memories = []

    for mem in memories:
        emb = mem.get("embedding", [])
        if isinstance(emb, str):
            try:
                emb = json.loads(emb)
            except Exception:
                continue
        if isinstance(emb, list) and len(emb) > 0:
            vectors.append(emb)
            valid_memories.append(mem)

    if not vectors:
        print("[FAISS] No embeddings found â€” run update_embeddings.py first")
        return

    matrix = np.array(vectors, dtype=np.float32)

    if FAISS_AVAILABLE:
        dim    = matrix.shape[1]
        _index = faiss.IndexFlatIP(dim)
        faiss.normalize_L2(matrix)
        _index.add(matrix)
    else:
        _index = matrix

    _indexed_memories = valid_memories
    _id_to_pos = {m.get("id"): i for i, m in enumerate(valid_memories)}
    print(f"[FAISS] Index built: {len(valid_memories)} vectors, dim={matrix.shape[1]}")


def faiss_search(query: str, top_k: int = 30) -> list[dict]:
    """
    Returns top-K memories by embedding similarity.
    Uses query expansion for better recall on short queries.
    """
    global _index, _indexed_memories

    if _index is None or not _indexed_memories:
        return []

    # FIX: use query embedding with expansion
    q_vec = get_query_embedding(query)
    if not q_vec:
        return []

    q_emb = np.array([q_vec], dtype=np.float32)

    if FAISS_AVAILABLE:
        faiss.normalize_L2(q_emb)
        k = min(top_k, len(_indexed_memories))
        scores, indices = _index.search(q_emb, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            mem = dict(_indexed_memories[int(idx)])
            mem["score"] = float(score)
            results.append(mem)
        return results
    else:
        from numpy.linalg import norm
        q_norm = q_emb[0] / (norm(q_emb[0]) + 1e-9)
        scores_list = []
        for i, mem in enumerate(_indexed_memories):
            v = _index[i]
            v_norm = v / (norm(v) + 1e-9)
            scores_list.append((float(np.dot(q_norm, v_norm)), i))
        scores_list.sort(reverse=True)
        results = []
        for score, idx in scores_list[:top_k]:
            mem = dict(_indexed_memories[idx])
            mem["score"] = score
            results.append(mem)
        return results


def get_index_size() -> int:
    return len(_indexed_memories)


