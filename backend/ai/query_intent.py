from enum import Enum


class QueryIntent(str, Enum):
    SEARCH = "search"
    FACT = "fact"
    SUMMARY = "summary"
    PLAN = "plan"
    COMPARE = "compare"


def detect_intent(query: str) -> QueryIntent:
    q = query.lower().strip()

    if any(x in q for x in ["compare", "difference", "vs"]):
        return QueryIntent.COMPARE

    if any(x in q for x in ["summary", "summarize", "overview"]):
        return QueryIntent.SUMMARY

    if any(x in q for x in ["plan", "roadmap", "next", "should"]):
        return QueryIntent.PLAN

    if any(x in q for x in ["what", "where", "when", "who"]):
        return QueryIntent.FACT

    return QueryIntent.SEARCH


