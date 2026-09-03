"""
planner_service.py
AI Goal Planner
"""

from __future__ import annotations


def build_plan(query: str, memories: list[dict]):

    completed = []
    missing = []

    keywords = {
        "resume": "Resume",
        "passport": "Passport",
        "ielts": "IELTS",
        "visa": "Visa",
        "sop": "Statement of Purpose",
        "transcript": "Transcript",
        "certificate": "Certificates",
    }

    memory_text = " ".join(
        (m.get("title", "") + " " + m.get("description", "")).lower()
        for m in memories
    )

    for key, label in keywords.items():

        if key in memory_text:
            completed.append(label)

        else:
            missing.append(label)

    return {

        "completed": completed,

        "missing": missing,

        "progress": round(
            len(completed) /
            len(keywords) * 100,
            1,
        ),

        "next_steps": [

            f"Prepare {x}"
            for x in missing[:5]

        ],
    }


