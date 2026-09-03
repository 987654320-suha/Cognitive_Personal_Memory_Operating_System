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

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./reality_search.db")

# Render provides postgres:// which SQLAlchemy 2.0 requires to be postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

is_sqlite = "sqlite" in DATABASE_URL.lower()

engine_kwargs = {}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL production pool settings
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
