# ðŸ“ LOCATION: backend/alembic_migration.py
"""
alembic_migration.py
====================
Safe manual migration for adding ACMA columns to an existing DB.
Run this if you already have a populated 'memories' table and
cannot drop and recreate it.

Adds:
    memories.importance_score  FLOAT  DEFAULT 0.5
    memories.access_count      INTEGER DEFAULT 0
    chat_history table (new)

Usage:
    python alembic_migration.py

Safe to run multiple times â€” skips columns that already exist.
"""

import sqlite3
import os

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./reality_search.db").replace("sqlite:///", "")


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def table_exists(cursor, table: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


def run_migration():
    print(f"[Migration] Connecting to: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # â”€â”€ 1. Add importance_score to memories â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if table_exists(cur, "memories"):
        if not column_exists(cur, "memories", "importance_score"):
            cur.execute("ALTER TABLE memories ADD COLUMN importance_score FLOAT DEFAULT 0.5")
            print("[Migration] Added: memories.importance_score")
        else:
            print("[Migration] Already exists: memories.importance_score")

        if not column_exists(cur, "memories", "access_count"):
            cur.execute("ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0")
            print("[Migration] Added: memories.access_count")
        else:
            print("[Migration] Already exists: memories.access_count")
    else:
        print("[Migration] Table 'memories' not found â€” run create_db.py first")

    # â”€â”€ 2. Create goals table if missing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if not table_exists(cur, "goals"):
        cur.execute("""
            CREATE TABLE goals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                parent_id   INTEGER REFERENCES goals(id),
                status      TEXT DEFAULT 'active',
                progress    FLOAT DEFAULT 0.0
            )
        """)
        print("[Migration] Created: goals table")
    else:
        print("[Migration] Already exists: goals table")

    # â”€â”€ 3. Create goal_memories edge table if missing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if not table_exists(cur, "goal_memories"):
        cur.execute("""
            CREATE TABLE goal_memories (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id          INTEGER NOT NULL REFERENCES goals(id),
                memory_id        INTEGER NOT NULL REFERENCES memories(id),
                relevance_weight FLOAT DEFAULT 1.0,
                UNIQUE(goal_id, memory_id)
            )
        """)
        print("[Migration] Created: goal_memories table")
    else:
        print("[Migration] Already exists: goal_memories table")

    # â”€â”€ 4. Create chat_history table if missing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if not table_exists(cur, "chat_history"):
        cur.execute("""
            CREATE TABLE chat_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS ix_chat_history_session ON chat_history(session_id)")
        print("[Migration] Created: chat_history table")
    else:
        print("[Migration] Already exists: chat_history table")

    conn.commit()
    conn.close()
    print("[Migration] Done. All tables and columns are up to date.")


if __name__ == "__main__":
    run_migration()


