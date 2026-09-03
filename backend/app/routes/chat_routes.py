"""
app/routes/chat_routes.py
==========================
Chat endpoint â€” RAG over ACMA-ranked memories.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database.database import get_db
from ai.chat_service import chat_with_memories

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    history: Optional[list[dict]] = None


@router.post("/")
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Ask a question over your memories.
    Returns answer + which memories were used + why (ACMA activation trace).
    """
    result = chat_with_memories(
        query=payload.query,
        db=db,
        conversation_history=payload.history,
    )
    return result


