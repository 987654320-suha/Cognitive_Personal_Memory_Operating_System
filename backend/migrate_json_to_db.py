"""
migrate_json_to_db.py
=====================
Migrates memories from data/memories.json to SQLite.
Sets importance_score and access_count for all migrated records.
Run ONCE after switching from JSON storage.
"""

import json
from pathlib import Path

from database.database import SessionLocal
from app.models.memory import Memory
from ai.importance_scorer import score_importance

JSON_FILE = Path("data/memories.json")

if not JSON_FILE.exists():
    print(f"[Migrate] {JSON_FILE} not found. Nothing to migrate.")
    exit(0)

with open(JSON_FILE, "r", encoding="utf-8") as f:
    memories = json.load(f)

db = SessionLocal()
migrated = 0
skipped = 0

for mem in memories:
    # Skip if already in DB (idempotent)
    title = mem.get("title", "")
    source = mem.get("source", "")
    exists = db.query(Memory).filter(Memory.source == source, Memory.title == title).first()
    if exists:
        skipped += 1
        continue

    text = mem.get("description", "") or ""
    importance = score_importance(title, text)

    db_memory = Memory(
        title=title,
        description=mem.get("description"),
        source=source,
        file_type=mem.get("file_type"),
        image=mem.get("image"),
        date=mem.get("date"),
        location=mem.get("location"),
        embedding=json.dumps(mem.get("embedding", [])),
        objects=json.dumps(mem.get("objects", [])),
        importance_score=importance,
        access_count=0,
    )
    db.add(db_memory)
    migrated += 1

db.commit()
db.close()

print(f"[Migrate] Done. Migrated: {migrated}, Skipped (already exist): {skipped}")


