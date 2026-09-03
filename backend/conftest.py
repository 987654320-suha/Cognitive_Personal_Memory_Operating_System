# ðŸ“ LOCATION: backend/conftest.py
"""
conftest.py
===========
Pytest fixtures shared across all test files.
Uses an in-memory SQLite DB so tests never touch production data.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from database.database import Base, get_db
from app.models.memory      import Memory
from app.models.goal        import Goal
from app.models.goal_memory import GoalMemory
from app.models.relationship import MemoryRelationship
from app.services.chat_history import ChatHistory
from main import app

# â”€â”€ In-memory test DB â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

TEST_DB_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db():
    """Fresh in-memory DB for each test function."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db):
    """FastAPI test client with DB override."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_memories(db):
    """Seeds 3 sample memories into the test DB."""
    import json
    memories = [
        Memory(
            title="Resume 2024",
            description="Software engineer resume with Python and FastAPI experience",
            source="resume.pdf",
            file_type="pdf",
            embedding=json.dumps([0.1] * 384),
            objects=json.dumps([]),
            importance_score=0.9,
            access_count=5,
        ),
        Memory(
            title="IELTS Certificate",
            description="IELTS overall band score 7.5 certificate",
            source="ielts.jpg",
            file_type="jpg",
            embedding=json.dumps([0.2] * 384),
            objects=json.dumps(["certificate", "document"]),
            importance_score=0.95,
            access_count=2,
        ),
        Memory(
            title="Car Photo",
            description="Photo of my car in the parking lot",
            source="car.jpg",
            file_type="jpg",
            embedding=json.dumps([0.9] * 384),
            objects=json.dumps(["car", "vehicle"]),
            importance_score=0.2,
            access_count=0,
        ),
    ]
    for m in memories:
        db.add(m)
    db.commit()
    return memories


@pytest.fixture
def sample_goals(db, sample_memories):
    """Seeds goals and links them to sample memories."""
    goal = Goal(name="Germany Masters", description="Applying for MS in Germany", status="active")
    db.add(goal)
    db.commit()

    edge1 = GoalMemory(goal_id=goal.id, memory_id=sample_memories[0].id, relevance_weight=1.0)
    edge2 = GoalMemory(goal_id=goal.id, memory_id=sample_memories[1].id, relevance_weight=1.0)
    db.add(edge1)
    db.add(edge2)
    db.commit()

    return [goal]


