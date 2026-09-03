# ðŸ“ LOCATION: backend/update_embeddings.py
"""
update_embeddings.py  â€” ACCURACY FIX v2
==========================================
Backfills ALL existing memories with:
  1. New high-quality embeddings (all-mpnet-base-v2, full text, enriched title)
  2. Correct importance scores
  3. Rebuilds both FAISS and BM25 indexes after completion

Run this whenever:
  - You change the embedding model
  - You add new memories in bulk
  - Search accuracy is poor on existing data
"""

import json
from database.database import SessionLocal
from app.models.memory import Memory
from ai.embedding_service import get_embedding
from ai.importance_scorer import score_importance

# Must match pipeline enrichment patterns
import re
_TITLE_ENRICHMENTS = {
    r"resume|cv":                     "resume cv curriculum vitae work experience",
    r"ielts|toefl|gre|gmat":          "language test english proficiency score certificate",
    r"passport":                       "passport identity travel document visa",
    r"certificate|cert|diploma":       "certificate award achievement completion",
    r"bank|statement":                 "bank statement financial account transaction",
    r"invoice|receipt":                "invoice receipt bill payment",
    r"degree|bachelor|master":         "degree university graduation academic",
    r"transcript|marksheet":           "transcript academic record grades marks",
}

def enrich(title: str, text: str) -> str:
    combined = (title + " " + text[:200]).lower()
    extras = []
    for pattern, keywords in _TITLE_ENRICHMENTS.items():
        if re.search(pattern, combined):
            extras.append(keywords)
    return f"{title} {' '.join(extras)}" if extras else title


db = SessionLocal()
memories = db.query(Memory).all()
total = len(memories)
print(f"[UpdateEmbeddings] Processing {total} memories...")

updated_emb = 0
updated_imp = 0

for i, mem in enumerate(memories):
    changed = False

    title = mem.title or ""
    desc  = mem.description or ""

    # Always recompute embedding with enriched title + full description
    enriched = enrich(title, desc)
    embed_text = f"{enriched}\n\n{desc[:3500]}"
    emb = get_embedding(embed_text)
    if emb:
        mem.embedding = json.dumps(emb)
        updated_emb += 1
        changed = True

    # Recompute importance score
    score = score_importance(title, desc)
    mem.importance_score = score
    updated_imp += 1
    changed = True

    if changed:
        db.add(mem)

    if (i + 1) % 20 == 0:
        db.commit()
        print(f"  {i+1}/{total} processed...")

db.commit()
db.close()

print(f"\n[UpdateEmbeddings] Done.")
print(f"  Embeddings updated:       {updated_emb}")
print(f"  Importance scores updated: {updated_imp}")

# Rebuild both search indexes
print("\n[UpdateEmbeddings] Rebuilding FAISS + BM25 indexes...")
from app.services.database_service import get_all_memories
from ai.faiss_service import build_index
from ai.hybrid_search import build_bm25

all_memories = get_all_memories()
build_index(all_memories)
build_bm25(all_memories)
print(f"[UpdateEmbeddings] Indexes rebuilt with {len(all_memories)} memories. Search is ready.")


