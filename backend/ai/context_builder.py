from __future__ import annotations


MAX_CONTEXT_CHARS = 3500


def build_context(memories: list[dict]):
    """
    Build a formatted context string from ACMA-ranked memories.
    Includes relationship information so LLM knows WHY documents are related.
    """
    context = []
    chars = 0
    goal_context = []
    used = []

    for mem in memories:
        # Build relationship block if available
        relationship = ""
        if mem.get("relationship_type"):
            relationship = f"""
RELATED VIA:
{mem['relationship_type']}

Relationship Strength:
{round(mem.get('relationship_strength', 0), 2)}
"""

        # Build the full memory block
        block = f"""
TITLE:
{mem.get("title", "")}

DESCRIPTION:
{mem.get("description", "")}

{relationship}

GOALS:
{", ".join(mem.get("matched_goals", []))}

CONFIDENCE:
{round(mem.get("confidence", 90), 1)}%
"""

        # Check if we have room for this block
        if chars + len(block) > MAX_CONTEXT_CHARS:
            break

        chars += len(block)
        context.append(block)
        used.append(mem)
        goal_context.extend(mem.get("matched_goals", []))

    return {
        "context": "\n----------------------\n".join(context),
        "goal_context": sorted(set(goal_context)),
        "memories": used,
    }


