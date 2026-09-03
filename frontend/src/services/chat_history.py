# 📁 LOCATION: backend/app/services/chat_history.py
"""
chat_history.py — Cognisphere
FIXED: auto-creates table, null-safe, proper error handling.
"""

from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.exc import OperationalError
from database.database import Base, SessionLocal


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(String,  index=True, nullable=False)
    role       = Column(String,  nullable=False)
    content    = Column(Text,    nullable=False)
    created_at = Column(String,  default=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self):
        return {
            "id":         self.id,
            "session_id": self.session_id,
            "role":       self.role,
            "content":    self.content,
            "created_at": self.created_at,
        }


def _ensure_table():
    """Create table if it doesn't exist yet."""
    try:
        from database.database import engine
        Base.metadata.create_all(bind=engine, tables=[ChatHistory.__table__])
    except Exception as e:
        print(f"[ChatHistory] Table create error: {e}")


def save_turn(session_id: str, role: str, content: str) -> None:
    _ensure_table()
    db = SessionLocal()
    try:
        turn = ChatHistory(session_id=session_id, role=role, content=content or "")
        db.add(turn)
        db.commit()
    except Exception as e:
        print(f"[ChatHistory] Save error: {e}")
        db.rollback()
    finally:
        db.close()


def get_history(session_id: str, last_n: int = 10) -> list[dict]:
    _ensure_table()
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
    except Exception as e:
        print(f"[ChatHistory] Get error: {e}")
        return []
    finally:
        db.close()


def clear_history(session_id: str) -> int:
    _ensure_table()
    db = SessionLocal()
    try:
        count = db.query(ChatHistory).filter(ChatHistory.session_id == session_id).delete()
        db.commit()
        return count
    except Exception as e:
        print(f"[ChatHistory] Clear error: {e}")
        return 0
    finally:
        db.close()


def list_sessions() -> list[str]:
    _ensure_table()
    db = SessionLocal()
    try:
        rows = db.query(ChatHistory.session_id).distinct().all()
        return [r[0] for r in rows]
    except Exception:
        return []
    finally:
        db.close()