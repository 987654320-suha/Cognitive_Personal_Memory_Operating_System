# 📁 LOCATION: backend/scripts/seed_goals.py
"""
seed_goals.py
=============
Pre-seeds the database with common life goals.
Run once after create_db.py on a fresh installation.

Usage:
    python scripts/seed_goals.py
"""

from database.database import SessionLocal
from backend.app.models.goal import Goal

SEED_GOALS = [
    {
        "name": "Germany Masters",
        "description": "Applying for Masters degree in Germany — IELTS, APS, university applications",
        "parent_id": None,
        "status": "active",
    },
    {
        "name": "Career",
        "description": "Job applications, resume, internships, placements",
        "parent_id": None,
        "status": "active",
    },
    {
        "name": "Certifications",
        "description": "Online courses, Udemy, Coursera, completion certificates",
        "parent_id": None,
        "status": "active",
    },
    {
        "name": "Projects",
        "description": "Personal and academic projects, GitHub, portfolio",
        "parent_id": None,
        "status": "active",
    },
    {
        "name": "Travel / Visa",
        "description": "Passport, visa applications, travel bookings",
        "parent_id": None,
        "status": "active",
    },
    {
        "name": "Finance",
        "description": "Bank statements, invoices, expenses, tax documents",
        "parent_id": None,
        "status": "active",
    },
    {
        "name": "Health",
        "description": "Medical records, prescriptions, hospital documents",
        "parent_id": None,
        "status": "active",
    },
    {
        "name": "Education",
        "description": "Degree certificates, transcripts, academic records",
        "parent_id": None,
        "status": "active",
    },
]


def seed():
    db = SessionLocal()
    created = 0
    skipped = 0

    for goal_data in SEED_GOALS:
        existing = db.query(Goal).filter(Goal.name == goal_data["name"]).first()
        if existing:
            skipped += 1
            continue
        goal = Goal(**goal_data)
        db.add(goal)
        created += 1

    db.commit()
    db.close()
    print(f"[SeedGoals] Created: {created}, Skipped (already exist): {skipped}")


if __name__ == "__main__":
    seed()
