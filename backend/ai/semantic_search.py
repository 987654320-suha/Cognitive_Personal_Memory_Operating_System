# ðŸ“ LOCATION: backend/ai/semantic_search.py

"""
semantic_search.py

Hybrid search:
BM25 + FAISS + filename matching â†’ ACMA re-ranking
"""

from __future__ import annotations

import time

from sqlalchemy.orm import Session

from ai.faiss_service import faiss_search
from ai.hybrid_search import hybrid_search, detect_query_type
from ai.acma_engine import ACMAEngine
from ai.gama_service import GAMAService
from app.services.database_service import get_all_memories


_acma = ACMAEngine()

def acma_search(
    query: str,
    db: Session,
    top_k: int = 10,
    weights: dict = None,
    user_id: int | None = None,
) -> list[dict]:

    t_total = time.time()

    all_memories = get_all_memories(user_id=user_id)

    if not all_memories:
        return []

    from ai.hybrid_search import detect_query_type

    query_type = detect_query_type(query)

    print(f"[ACMA] Query type: {query_type}")

    # =========================================================
    # FAST PROJECT / FILE NAME DETECTION
    # =========================================================
    #
    # If the user mentions an existing memory title or filename,
    # do NOT run the expensive SentenceTransformer/FAISS query.
    #
    # Example:
    #   "tell me about my YORAI project"
    #
    # YORAI exists in memory titles.
    #
    # Therefore:
    #
    #   BM25 + filename matching
    #           â†“
    #       ACMA ranking
    #
    # instead of:
    #
    #   SentenceTransformer
    #           â†“
    #       FAISS
    #           â†“
    #       BM25
    #           â†“
    #       ACMA
    #
    # =========================================================

    q_lower = query.lower()

    exact_memory_signal = False

    for mem in all_memories:

        title = str(
            mem.get("title") or ""
        ).lower()

        source = str(
            mem.get("source") or ""
        ).lower()

        if not title and not source:
            continue

        # -----------------------------------------------------
        # Exact title match
        # -----------------------------------------------------

        if title and title in q_lower:
            exact_memory_signal = True
            print(
                f"[ACMA] Exact memory title detected: "
                f"{mem.get('title')}"
            )
            break

        # -----------------------------------------------------
        # Exact filename/source match
        # -----------------------------------------------------

        if source and source in q_lower:
            exact_memory_signal = True
            print(
                f"[ACMA] Exact memory source detected: "
                f"{mem.get('source')}"
            )
            break

        # -----------------------------------------------------
        # Multi-word title matching
        # -----------------------------------------------------

        if title:
            title_words = [
                w for w in title.split()
                if len(w) >= 3
            ]

            if title_words:

                matched = sum(
                    1
                    for word in title_words
                    if word in q_lower
                )

                # At least one distinctive title word
                if matched >= 1:
                    exact_memory_signal = True

                    print(
                        f"[ACMA] Memory keyword detected: "
                        f"{mem.get('title')}"
                    )

                    break

    # =========================================================
    # RETRIEVAL
    # =========================================================

    faiss_results = []

    # ---------------------------------------------------------
    # FAST PATH
    # ---------------------------------------------------------
    #
    # Existing memory/project mentioned:
    #
    # "tell me about my YORAI project"
    #
    # Don't spend ~12 sec generating a query embedding.
    # BM25 + filename retrieval is already ideal here.
    # ---------------------------------------------------------

    if exact_memory_signal:

        print(
            "[ACMA] FAST PATH: "
            "skipping FAISS because an existing memory/project "
            "was detected."
        )

    # ---------------------------------------------------------
    # NORMAL SEMANTIC PATH
    # ---------------------------------------------------------

    elif query_type in ("semantic", "mixed"):

        t_faiss = time.time()

        faiss_results = faiss_search(
            query,
            top_k=min(top_k * 2, 6),
        )

        print(
            f"[PERF] FAISS: "
            f"{time.time() - t_faiss:.3f} sec "
            f"({len(faiss_results)} results)"
        )

    # =========================================================
    # HYBRID SEARCH
    # =========================================================

    t_hybrid = time.time()

    hybrid_results = hybrid_search(
        query=query,
        faiss_results=faiss_results,
        all_memories=all_memories,
        top_k=min(top_k * 2, 6),
    )

    print(
        f"[PERF] HYBRID: "
        f"{time.time() - t_hybrid:.3f} sec "
        f"({len(hybrid_results)} results)"
    )

    if not hybrid_results:
        return []

    # =========================================================
    # GAMA
    # =========================================================

    t_gama = time.time()

    gama = GAMAService(db)

    active_goals = gama.get_active_goals()
    goal_memory_map = gama.get_goal_memory_map()

    print(
        f"[PERF] GAMA: "
        f"{time.time() - t_gama:.3f} sec"
    )

    # =========================================================
    # ACMA RE-RANK
    # =========================================================

    t_acma = time.time()

    activations = _acma.rank(
        query=query,
        hybrid_results=hybrid_results,
        all_memories=all_memories,
        active_goals=active_goals,
        goal_memory_map=goal_memory_map,
        weights=weights,
    )

    print(
        f"[PERF] ACMA RANK: "
        f"{time.time() - t_acma:.3f} sec"
    )

    # =========================================================
    # ACCESS COUNT
    # =========================================================

    top_ids = [
        a.memory_id
        for a in activations[:top_k]
    ]

    t_access = time.time()

    _increment_access(
        db,
        top_ids,
    )

    print(
        f"[PERF] ACCESS UPDATE: "
        f"{time.time() - t_access:.3f} sec"
    )

    print(
        f"[PERF] TOTAL ACMA: "
        f"{time.time() - t_total:.3f} sec"
    )

    return [
        a.to_dict()
        for a in activations[:top_k]
    ]
    # ---------------------------------------------------------
    # 8. FINAL RESULT
    # ---------------------------------------------------------

    results = [
        a.to_dict()
        for a in activations[:top_k]
    ]

    print(
        f"[PERF] TOTAL ACMA: "
        f"{time.time() - total_start:.3f} sec"
    )

    return results


def semantic_search(
    query: str,
    top_k: int = 10,
    user_id: int | None = None,
) -> list[dict]:

    """
    Fast search without ACMA re-ranking.
    Used for autocomplete/previews.
    """

    all_memories = get_all_memories(user_id=user_id)

    if not all_memories:
        return []

    faiss_results = faiss_search(
        query,
        top_k=top_k * 3,
    )

    hybrid_results = hybrid_search(
        query,
        faiss_results,
        all_memories,
        top_k=top_k,
    )

    for result in hybrid_results:
        result.pop("embedding", None)

    return hybrid_results


def invalidate_search_cache() -> None:
    """
    Kept for backward compatibility.

    BM25 is rebuilt during startup and after imports.
    """
    pass


def _increment_access(
    db: Session,
    memory_ids: list[int],
) -> None:

    if not memory_ids:
        return

    try:
        from app.models.memory import Memory

        db.query(Memory).filter(
            Memory.id.in_(memory_ids)
        ).update(
            {
                Memory.access_count:
                Memory.access_count + 1
            },
            synchronize_session="fetch",
        )

        db.commit()

    except Exception as e:
        print(
            f"[Search] access_count update failed: {e}"
        )


