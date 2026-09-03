# ðŸ“ LOCATION: backend/app/services/chat_history.py
"""
chat_history.py
===============
Stores and retrieves per-session conversation history in SQLite.
Each session is identified by a session_id (UUID string).
History is used by chat_service.py for multi-turn context.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text
from database.database import Base, SessionLocal


# â”€â”€ Model â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    role       = Column(String, nullable=False)   # "user" | "assistant"
    content    = Column(Text,   nullable=False)
    created_at = Column(String, default=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self):
        return {
            "id":         self.id,
            "session_id": self.session_id,
            "role":       self.role,
            "content":    self.content,
            "created_at": self.created_at,
        }


# â”€â”€ Service functions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def save_turn(session_id: str, role: str, content: str) -> None:
    """Persist one conversation turn."""
    db = SessionLocal()
    try:
        turn = ChatHistory(session_id=session_id, role=role, content=content)
        db.add(turn)
        db.commit()
    finally:
        db.close()


def get_history(session_id: str, last_n: int = 10) -> list[dict]:
    """Return the last N turns for a session, oldest first."""
    db = SessionLocal()
    try:
        rows = (
            db.query(ChatHistory)
            .filter(ChatHistory.session_id == session_id)
            .order_by(ChatHistory.id.desc())
            .limit(last_n)
            .all()
        )
        return [r.to_dict() for r in reversed(rows)]
    finally:
        db.close()


def clear_history(session_id: str) -> int:
    """Delete all history for a session. Returns rows deleted."""
    db = SessionLocal()
    try:
        count = db.query(ChatHistory).filter(ChatHistory.session_id == session_id).delete()
        db.commit()
        return count
    finally:
        db.close()


def list_sessions() -> list[str]:
    """Return all unique session IDs."""
    db = SessionLocal()
    try:
        rows = db.query(ChatHistory.session_id).distinct().all()
        return [r[0] for r in rows]
    finally:
        db.close()


