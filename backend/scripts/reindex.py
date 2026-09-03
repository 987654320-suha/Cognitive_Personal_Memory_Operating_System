# 📁 LOCATION: backend/scripts/reindex.py
"""
reindex.py
==========
Master reindex script — run this whenever search accuracy drops.
Rebuilds embeddings, FAISS, and BM25 from scratch.

Usage:
    python scripts/reindex.py
    python scripts/reindex.py --model all-mpnet-base-v2
"""

import argparse
import json
import re
import sys
from database.database import SessionLocal
from backend.app.models.memory import Memory

_TITLE_ENRICHMENTS = {
    r"resume|cv":              "resume cv curriculum vitae work experience",
    r"ielts|toefl|gre|gmat":  "language test english proficiency certificate",
    r"passport":               "passport identity travel document",
    r"certificate|diploma":    "certificate award achievement completion",
    r"bank|statement":         "bank statement financial",
    r"invoice|receipt":        "invoice receipt payment",
    r"degree|bachelor|master": "degree university graduation",
    r"transcript|marksheet":   "transcript academic record grades",
}

def enrich(title: str, text: str) -> str:
    combined = (title + " " + text[:200]).lower()
    extras = []
    for pattern, keywords in _TITLE_ENRICHMENTS.items():
        if re.search(pattern, combined):
            extras.append(keywords)
    return f"{title} {' '.join(extras)}" if extras else title


def run(model_name: str = "all-mpnet-base-v2"):
    print(f"\n══ NexusMind Reindex ══════════════════════════════")
    print(f"Model: {model_name}")

    from ai.embedding_service import get_embedding, _get_model
    _get_model()  # warm up

    db = SessionLocal()
    memories = db.query(Memory).all()
    print(f"Memories to process: {len(memories)}")

    for i, mem in enumerate(memories):
        title = mem.title or mem.source or ""
        desc  = mem.description or ""
        enriched   = enrich(title, desc)
        embed_text = f"{enriched}\n\n{desc[:3500]}"
        emb = get_embedding(embed_text)
        if emb:
            mem.embedding = json.dumps(emb)
        db.add(mem)
        if (i + 1) % 10 == 0:
            db.commit()
            print(f"  {i+1}/{len(memories)}", end="\r", flush=True)

    db.commit()
    db.close()
    print(f"\n✓ Embeddings regenerated")

    # Rebuild indexes
    from backend.app.services.database_service import get_all_memories
    from ai.faiss_service import build_index
    from ai.hybrid_search import build_bm25

    all_mems = get_all_memories()
    build_index(all_mems)
    build_bm25(all_mems)

    print(f"✓ FAISS index built ({len(all_mems)} vectors)")
    print(f"✓ BM25 index built ({len(all_mems)} documents)")
    print(f"\n══ Reindex complete. Search accuracy should be restored. ══\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="all-mpnet-base-v2")
    args = parser.parse_args()
    run(args.model)
