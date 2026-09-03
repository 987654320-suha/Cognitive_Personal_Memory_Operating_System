from ai.planner_service import build_plan

def generate_insights(memories, goals):
    plan = build_plan("", memories)

    frequent = sorted(
        memories,
        key=lambda m: m.get("access_count", 0),
        reverse=True,
    )[:5]

    return {
        "memory_count": len(memories),
        "goal_count": len(goals),
        "missing_documents": plan["missing"],
        "completed_documents": plan["completed"],
        "top_memories": [
            {
                "id": m["id"],
                "title": m["title"]
            }
            for m in frequent
        ]
    }


