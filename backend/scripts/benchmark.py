# 📁 LOCATION: backend/scripts/benchmark.py
"""
benchmark.py
============
Measures retrieval quality of ACMA vs plain FAISS search.
Produces precision, recall, and latency metrics.

This is the research evaluation script for the patent/paper.
Run after ingesting a meaningful set of memories.

Usage:
    python scripts/benchmark.py
    python scripts/benchmark.py --queries 20 --top-k 10
"""

from __future__ import annotations
import time
import argparse
import json

# ── Ground truth query set (manually labeled) ────────────────────────────────
# Format: {query: [expected_title_keywords]}
GROUND_TRUTH = {
    "germany masters":        ["ielts", "passport", "resume", "aps", "germany"],
    "resume cv":              ["resume", "cv", "curriculum"],
    "certificate course":     ["certificate", "udemy", "coursera", "completion"],
    "bank statement finance": ["bank", "statement", "invoice", "expense"],
    "passport visa":          ["passport", "visa"],
    "project github":         ["project", "github", "portfolio"],
}


def precision_at_k(results: list[dict], expected_keywords: list[str], k: int) -> float:
    top_k = results[:k]
    relevant = 0
    for r in top_k:
        title_lower = (r.get("title") or "").lower()
        if any(kw.lower() in title_lower for kw in expected_keywords):
            relevant += 1
    return relevant / k if k > 0 else 0.0


def recall_at_k(results: list[dict], expected_keywords: list[str], k: int) -> float:
    top_k = results[:k]
    found_keywords = set()
    for r in top_k:
        title_lower = (r.get("title") or "").lower()
        for kw in expected_keywords:
            if kw.lower() in title_lower:
                found_keywords.add(kw)
    return len(found_keywords) / len(expected_keywords) if expected_keywords else 0.0


def run_benchmark(top_k: int = 10):
    from database.database import SessionLocal
    from ai.semantic_search import acma_search, semantic_search
    from ai.faiss_service import build_index
    from backend.app.services.database_service import get_all_memories

    print("\n══ CogniSphere Retrieval Benchmark ══════════════════════════")
    print(f"Top-K: {top_k} | Queries: {len(GROUND_TRUTH)}")
    print("─────────────────────────────────────────────────────────\n")

    memories = get_all_memories()
    if not memories:
        print("[Benchmark] No memories in DB. Ingest some files first.")
        return

    build_index(memories)
    db = SessionLocal()

    acma_metrics  = {"precision": [], "recall": [], "latency": []}
    faiss_metrics = {"precision": [], "recall": [], "latency": []}

    for query, expected in GROUND_TRUTH.items():
        # ── ACMA ──────────────────────────────────────────────────────────────
        t0 = time.perf_counter()
        acma_results = acma_search(query, db, top_k=top_k)
        acma_latency = (time.perf_counter() - t0) * 1000

        p_acma = precision_at_k(acma_results, expected, top_k)
        r_acma = recall_at_k(acma_results, expected, top_k)
        acma_metrics["precision"].append(p_acma)
        acma_metrics["recall"].append(r_acma)
        acma_metrics["latency"].append(acma_latency)

        # ── FAISS only ─────────────────────────────────────────────────────────
        t0 = time.perf_counter()
        faiss_results = semantic_search(query, top_k=top_k)
        faiss_latency = (time.perf_counter() - t0) * 1000

        p_faiss = precision_at_k(faiss_results, expected, top_k)
        r_faiss = recall_at_k(faiss_results, expected, top_k)
        faiss_metrics["precision"].append(p_faiss)
        faiss_metrics["recall"].append(r_faiss)
        faiss_metrics["latency"].append(faiss_latency)

        print(f"  Query: '{query}'")
        print(f"    ACMA  — P@{top_k}: {p_acma:.2f}  R@{top_k}: {r_acma:.2f}  {acma_latency:.0f}ms")
        print(f"    FAISS — P@{top_k}: {p_faiss:.2f}  R@{top_k}: {r_faiss:.2f}  {faiss_latency:.0f}ms\n")

    db.close()

    def avg(lst): return sum(lst) / len(lst) if lst else 0

    print("══ Summary ═══════════════════════════════════════════════")
    print(f"{'':10} {'Precision@K':>14} {'Recall@K':>10} {'Latency(ms)':>13}")
    print(f"{'ACMA':10} {avg(acma_metrics['precision']):>14.3f} {avg(acma_metrics['recall']):>10.3f} {avg(acma_metrics['latency']):>13.1f}")
    print(f"{'FAISS':10} {avg(faiss_metrics['precision']):>14.3f} {avg(faiss_metrics['recall']):>10.3f} {avg(faiss_metrics['latency']):>13.1f}")

    delta_p = avg(acma_metrics["precision"]) - avg(faiss_metrics["precision"])
    delta_r = avg(acma_metrics["recall"])    - avg(faiss_metrics["recall"])
    print(f"\nACMA improvement: ΔPrecision={delta_p:+.3f}  ΔRecall={delta_r:+.3f}")
    print("══════════════════════════════════════════════════════════\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()
    run_benchmark(top_k=args.top_k)
