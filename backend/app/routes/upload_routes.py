"""
app/routes/upload_routes.py
============================
File upload endpoint â€” runs the full memory pipeline.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.memory_service import ingest_uploaded_file
from app.services.database_service import refresh_memory_cache, get_all_memories
from ai.faiss_service import build_index
from ai.hybrid_search import build_bm25

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file (image, PDF, DOCX, text).
    Runs OCR â†’ Object Detection â†’ Embedding â†’ SQLite â†’ FAISS â†’ GAMA.
    Returns the saved memory with ACMA metadata.
    """
    ALLOWED_TYPES = {
        "image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}",
        )

    try:
        file_bytes = await file.read()
        result = ingest_uploaded_file(file_bytes, file.filename)
        
        # âœ… Refresh in-memory cache after successful database commit
        refresh_memory_cache()
        print(f"[Upload] Memory cache refreshed after uploading: {file.filename}")
        
        # âœ… Rebuild FAISS index with the new memory
        memories = get_all_memories()
        if memories:
            build_index(memories)
            print(f"[Upload] FAISS index rebuilt with {len(memories)} memories")
            
            # âœ… Rebuild BM25 index for keyword search
            build_bm25(memories)
            print(f"[Upload] BM25 index rebuilt with {len(memories)} memories")
        
        return {"success": True, "memory": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


