"""
app/routes/experiment_routes.py
================================
Ablation experiment endpoint.

POST /experiment/search

Accepts a query + ExperimentConfig (toggle individual algorithm components)
and returns full per-channel breakdown showing exactly how each part
of the pipeline contributes to the final ranking.

Supports all ablation variants from the paper:
  A: FAISS-only (semantic baseline)
  B: Hybrid RRF (no ACMA)
  C: Hybrid + Goal
  D: Hybrid + Goal + Relationship
  E: Hybrid + Goal + Relationship + Importance/Temporal/Access
  F: Full ACMA (all components)
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database.database import get_db

router = APIRouter(prefix="/experiment", tags=["experiment"])


# â”€â”€ Schemas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ExperimentConfig(BaseModel):
    query: str

    # Retrieval channels
    use_faiss:    bool = True
    use_bm25:     bool = True
    use_title:    bool = True

    # RRF
    use_rrf:      bool = True

    # ACMA components
    use_acma:     bool = True
    acma_goal:         bool = True
    acma_relationship: bool = True
    acma_importance:   bool = True
    acma_temporal:     bool = True
    acma_access:       bool = True
    acma_title_boost:  bool = True

    # ACMA weights (optional override â€” if None, uses defaults)
    weight_semantic:      Optional[float] = None
    weight_goal:          Optional[float] = None
    weight_relationship:  Optional[float] = None
    weight_importance:    Optional[float] = None
    weight_temporal:      Optional[float] = None
    weight_access:        Optional[float] = None

    top_k: int = 10


# â”€â”€ Experiment endpoint â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/search")
def experiment_search(config: ExperimentConfig, db: Session = Depends(get_db)):
    """
    Configurable search that exposes every stage of the pipeline.

    Returns:
      - faiss_results     : raw FAISS cosine similarity results
      - bm25_results      : raw BM25 keyword match results
      - title_results     : filename/title exact match results
      - rrf_results       : RRF-merged ranking (if use_rrf=True)
      - acma_results      : ACMA re-ranked results with component scores
      - config_used       : the ExperimentConfig that was applied
    """
    from ai.faiss_service import faiss_search
    from ai.hybrid_search import BM25, _bm25, filename_match_score, rrf_merge
    from ai.acma_engine import ACMAEngine, DEFAULT_WEIGHTS
    from ai.gama_service import GAMAService
    from app.services.database_service import get_all_memories
    import math

    all_memories = get_all_memories()
    if not all_memories:
        return {"error": "No memories indexed", "results": []}

    # â”€â”€ Channel 1: FAISS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    faiss_results = []
    if config.use_faiss:
        raw = faiss_search(config.query, top_k=config.top_k * 3)
        faiss_results = [
            {
                "id":          r.get("id"),
                "title":       r.get("title", ""),
                "description": r.get("description", "")[:200],
                "score":       round(r.get("score", 0), 4),
                "channel":     "faiss",
            }
            for r in raw
        ]

    # â”€â”€ Channel 2: BM25 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    bm25_results = []
    if config.use_bm25:
        mem_index = {m["id"]: m for m in all_memories}
        raw_bm25 = _bm25.score(config.query, top_k=config.top_k * 3)
        for idx, score in raw_bm25:
            if idx < len(all_memories):
                m = all_memories[idx]
                bm25_results.append({
                    "id":          m.get("id"),
                    "title":       m.get("title", ""),
                    "description": m.get("description", "")[:200],
                    "score":       round(score, 4),
                    "channel":     "bm25",
                })

    # â”€â”€ Channel 3: Title / Filename â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    title_results = []
    if config.use_title:
        scored = [
            (m, filename_match_score(config.query, m))
            for m in all_memories
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        title_results = [
            {
                "id":          m.get("id"),
                "title":       m.get("title", ""),
                "description": m.get("description", "")[:200],
                "score":       round(sc, 4),
                "channel":     "title",
            }
            for m, sc in scored if sc > 0
        ][:config.top_k * 2]

    # â”€â”€ RRF Merge â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    rrf_results = []
    if config.use_rrf:
        channels = []
        weights  = []
        if config.use_faiss and faiss_results:
            channels.append([_enrich(r, all_memories) for r in faiss_results])
            weights.append(1.0)
        if config.use_bm25 and bm25_results:
            channels.append([_enrich(r, all_memories) for r in bm25_results])
            weights.append(3.5)
        if config.use_title and title_results:
            channels.append([_enrich(r, all_memories) for r in title_results])
            weights.append(6.0)

        if channels:
            merged = rrf_merge(channels, k=40, weights=weights)
            max_rrf = max((m.get("rrf_score", 0) for m in merged), default=1.0) or 1.0
            rrf_results = [
                {
                    "id":          m.get("id"),
                    "title":       m.get("title", ""),
                    "description": m.get("description", "")[:200],
                    "rrf_score":   round(m.get("rrf_score", 0), 6),
                    "normalized":  round(m.get("rrf_score", 0) / max_rrf, 4),
                    "channel":     "rrf",
                }
                for m in merged[:config.top_k * 2]
            ]

    # â”€â”€ ACMA Re-ranking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    acma_results = []
    if config.use_acma:
        # Build weights from config (zeroing out disabled components)
        weights_dict = {
            "semantic":     config.weight_semantic     if config.weight_semantic     is not None else DEFAULT_WEIGHTS["semantic"],
            "goal":         (config.weight_goal        if config.weight_goal         is not None else DEFAULT_WEIGHTS["goal"])        * (1.0 if config.acma_goal         else 0.0),
            "relationship": (config.weight_relationship if config.weight_relationship is not None else DEFAULT_WEIGHTS["relationship"]) * (1.0 if config.acma_relationship else 0.0),
            "importance":   (config.weight_importance  if config.weight_importance   is not None else DEFAULT_WEIGHTS["importance"])   * (1.0 if config.acma_importance   else 0.0),
            "temporal":     (config.weight_temporal    if config.weight_temporal     is not None else DEFAULT_WEIGHTS["temporal"])     * (1.0 if config.acma_temporal     else 0.0),
            "access":       (config.weight_access      if config.weight_access       is not None else DEFAULT_WEIGHTS["access"])      * (1.0 if config.acma_access       else 0.0),
        }

        # Build hybrid candidates (use whatever channels are enabled)
        hybrid_candidates = rrf_results if (config.use_rrf and rrf_results) else (
            faiss_results + bm25_results + title_results
        )

        # Enrich candidates with full memory data for ACMA
        enriched = [_enrich(r, all_memories) for r in hybrid_candidates]

        # GAMA context
        gama            = GAMAService(db)
        active_goals    = gama.get_active_goals()
        goal_memory_map = gama.get_goal_memory_map()

        # Disable title_boost in ACMA engine if toggled off
        engine = ACMAEngine(weights=weights_dict)
        if not config.acma_title_boost:
            # Monkey-patch title boost to zero
            engine._title_boost = lambda query, mem: 0.0

        activations = engine.rank(
            query           = config.query,
            hybrid_results  = enriched,
            all_memories    = all_memories,
            active_goals    = active_goals,
            goal_memory_map = goal_memory_map,
            weights         = weights_dict,
        )

        acma_results = [
            {
                **a.to_dict(),
                "description": (a.description or "")[:200],
                "channel":     "acma",
            }
            for a in activations[:config.top_k]
        ]

    # â”€â”€ Build config summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    config_summary = {
        "query":       config.query,
        "channels": {
            "faiss":  config.use_faiss,
            "bm25":   config.use_bm25,
            "title":  config.use_title,
        },
        "rrf":   config.use_rrf,
        "acma":  config.use_acma,
        "acma_components": {
            "goal":         config.acma_goal,
            "relationship": config.acma_relationship,
            "importance":   config.acma_importance,
            "temporal":     config.acma_temporal,
            "access":       config.acma_access,
            "title_boost":  config.acma_title_boost,
        },
        "top_k": config.top_k,
    }

    return {
        "config":        config_summary,
        "faiss_results": faiss_results[:config.top_k],
        "bm25_results":  bm25_results[:config.top_k],
        "title_results": title_results[:config.top_k],
        "rrf_results":   rrf_results[:config.top_k],
        "acma_results":  acma_results,
    }


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _enrich(partial: dict, all_memories: list[dict]) -> dict:
    """Fills in full memory data for a partial result dict."""
    mid = partial.get("id") or partial.get("memory_id")
    for m in all_memories:
        if m.get("id") == mid:
            merged = dict(m)
            merged["score"] = partial.get("score") or partial.get("rrf_score") or partial.get("normalized") or 0
            return merged
    return partial


