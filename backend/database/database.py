"""
database/database.py
====================
SQLAlchemy engine + session factory.
Single source of truth for DB connection.
Supports SQLite (local development) and PostgreSQL (production on Render).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

raw_url = os.getenv("DATABASE_URL")
if not raw_url or not raw_url.strip():
    raw_url = "sqlite:///./reality_search.db"
else:
    raw_url = raw_url.strip()

# Render provides postgres:// which SQLAlchemy 2.0 requires to be postgresql://
if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql://", 1)

DATABASE_URL = raw_url
is_sqlite = "sqlite" in DATABASE_URL.lower()

engine_kwargs = {}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL production pool settings
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

try:
    engine = create_engine(DATABASE_URL, **engine_kwargs)
except Exception as _e:
    print(f"[Database] Failed to initialize engine with {DATABASE_URL}: {_e}")
    print("[Database] Falling back safely to local SQLite.")
    DATABASE_URL = "sqlite:///./reality_search.db"
    is_sqlite = True
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
