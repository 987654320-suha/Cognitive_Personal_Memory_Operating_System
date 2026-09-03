# CogniSphere v2.0 — Upgrade Guide

## What changed

| Area | Before | After |
|------|--------|-------|
| Search | FAISS cosine similarity | ACMA 6-factor activation scoring |
| Goals | Basic Goal model | GAMA goal graph + progress reports |
| Memory model | title, description, embedding | + `importance_score`, `access_count` |
| Ingestion | Manual pipeline calls | Single `run_pipeline()` entry point |
| Chat | Basic RAG | RAG + explainability trace |
| Detection | No goal detection | Auto goal linking on ingest |

---

## Step-by-step setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create / migrate database tables
```bash
python create_db.py
```
This is safe to re-run. It creates `memories`, `goals`, `goal_memories` tables.
New columns `importance_score` and `access_count` are added to `memories`.

### 3. Migrate existing JSON data (if you have data/memories.json)
```bash
python migrate_json_to_db.py
```

### 4. Backfill embeddings and importance scores for existing records
```bash
python update_embeddings.py
```

### 5. Verify database state
```bash
python check_db.py
```

### 6. Start the backend
```bash
uvicorn main:app --reload --port 8000
```

---

## New API endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/search/?q=...&mode=acma` | ACMA-ranked semantic search |
| GET | `/search/?q=...&mode=fast` | FAISS-only fast search |
| GET | `/search/explain/{id}?q=...` | Activation breakdown for one memory |
| GET | `/goals/` | List all goals |
| POST | `/goals/` | Create a goal |
| GET | `/goals/{id}/progress` | Goal progress report (Explainable AI) |
| PATCH | `/goals/{id}/status` | Update goal status |
| GET | `/goals/memory/{id}` | Goals linked to a memory |
| POST | `/chat/` | Chat with memories (+ source trace) |
| GET | `/stats/` | System statistics |

---

## File structure

```
backend/
├── ai/
│   ├── acma_engine.py          ← ACMA 6-factor activation (NEW)
│   ├── gama_service.py         ← GAMA goal graph (NEW)
│   ├── memory_pipeline.py      ← Central ingestion hub (NEW)
│   ├── importance_scorer.py    ← Importance at ingest time (NEW)
│   ├── summarizer.py           ← LLM summary generation (NEW)
│   ├── semantic_search.py      ← ACMA + FAISS search (UPDATED)
│   ├── chat_service.py         ← RAG + explainability (UPDATED)
│   ├── goal_detector.py        ← Two-tier goal detection (UPDATED)
│   ├── embedding_service.py    ← Sentence embeddings (unchanged)
│   └── faiss_service.py        ← FAISS index (UPDATED)
├── app/
│   ├── models/
│   │   ├── memory.py           ← + importance_score, access_count (UPDATED)
│   │   ├── goal.py             ← Goal node (UPDATED)
│   │   └── goal_memory.py      ← Goal↔Memory edge (UPDATED)
│   ├── routes/
│   │   ├── search_routes.py    ← ACMA search endpoints (UPDATED)
│   │   ├── goal_routes.py      ← Goal CRUD + progress (UPDATED)
│   │   ├── upload_routes.py    ← Triggers pipeline (UPDATED)
│   │   ├── chat_routes.py      ← RAG chat (UPDATED)
│   │   ├── memory_routes.py    ← Memory CRUD (UPDATED)
│   │   └── stats_routes.py     ← System stats (UPDATED)
│   └── services/
│       ├── database_service.py ← DB helpers (UPDATED)
│       ├── memory_service.py   ← Memory service (UPDATED)
│       ├── goal_service.py     ← Goal service (NEW)
│       └── folder_watcher.py  ← Auto-ingest watcher (UPDATED)
├── database/database.py        ← SQLAlchemy setup
├── document/
│   ├── pdf_reader.py
│   └── docx_reader.py
├── vision/
│   ├── ocr.py
│   └── object_detector.py
├── vector_db/faiss_index.py    ← Persistent FAISS (NEW)
├── main.py                     ← FastAPI app (UPDATED)
├── create_db.py                ← DB setup script (UPDATED)
├── migrate_json_to_db.py       ← JSON → SQLite migration (UPDATED)
├── update_embeddings.py        ← Backfill script (UPDATED)
├── check_db.py                 ← DB verification (UPDATED)
└── requirements.txt
```

---

## ACMA Formula

```
A(m, q) = 0.35 * Semantic(m,q)
        + 0.25 * GoalRelevance(m,q)
        + 0.15 * RelationshipStrength(m)
        + 0.10 * Importance(m)
        + 0.10 * TemporalRelevance(m)
        + 0.05 * AccessHistory(m)
```

Weights are configurable at runtime via the `weights` parameter in `ACMAEngine.rank()`.

## GAMA Goal Progress Example

```
GET /goals/1/progress

{
  "goal": { "name": "Germany Masters", "status": "active" },
  "present": [
    { "title": "Resume", ... },
    { "title": "IELTS Certificate", ... }
  ],
  "missing_hints": ["Passport copy", "APS certificate", "Blocked account proof"],
  "completion_pct": 28.6
}
```
