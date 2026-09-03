# ðŸ“ LOCATION: backend/create_db.py
"""
create_db.py â€” Creates all CogniSphere tables.
Safe to re-run. Tables: memories, goals, goal_memories, chat_history
"""
from database.database import engine, Base
from app.models.memory       import Memory
from app.models.goal         import Goal
from app.models.goal_memory  import GoalMemory
from app.services.chat_history import ChatHistory

print("Creating / verifying database tables...")
Base.metadata.create_all(bind=engine)
print("Tables ready: memories, goals, goal_memories, chat_history")


