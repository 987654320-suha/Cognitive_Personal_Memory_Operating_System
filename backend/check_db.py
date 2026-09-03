"""
check_db.py
===========
Verify database state: tables, row counts, and ACMA column presence.
"""

from database.database import SessionLocal, engine
from app.models.memory import Memory
from app.models.goal import Goal
from app.models.goal_memory import GoalMemory
from sqlalchemy import inspect, text

db = SessionLocal()

print("\nâ”€â”€ DATABASE CHECK â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")

# Tables
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"\nTables: {tables}")

# Memories
memories = db.query(Memory).all()
print(f"\nMemories:     {len(memories)}")
for m in memories[:5]:
    print(f"  [{m.id}] {m.title[:40] if m.title else 'N/A':<40} imp={m.importance_score:.2f} access={m.access_count}")

# Goals
goals = db.query(Goal).all()
print(f"\nGoals:        {len(goals)}")
for g in goals:
    print(f"  [{g.id}] {g.name} | status={g.status}")

# Edges
edges = db.query(GoalMemory).count()
print(f"\nGoalâ†”Memory edges: {edges}")

# ACMA column check
has_importance = any(
    c["name"] == "importance_score"
    for c in inspector.get_columns("memories")
)
has_access = any(
    c["name"] == "access_count"
    for c in inspector.get_columns("memories")
)
print(f"\nACMA columns: importance_score={has_importance}, access_count={has_access}")
print("â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€\n")

db.close()


