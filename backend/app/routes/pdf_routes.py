# ðŸ“ LOCATION: backend/app/routes/pdf_routes.py
"""
pdf_routes.py
=============
PDF-specific endpoints â€” extract text, preview, search within PDF.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import tempfile
import os

router = APIRouter(prefix="/pdf", tags=["pdf"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/extract-text")
async def extract_pdf_text(file: UploadFile = File(...)):
    """
    Upload a PDF and get its extracted text back immediately.
    Does NOT save to DB â€” use /upload for full pipeline ingestion.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")

    tmp_path = None
    try:
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        from document.pdf_reader import read_pdf
        text = read_pdf(tmp_path)

        return {
            "filename":   file.filename,
            "text":       text,
            "char_count": len(text),
            "word_count": len(text.split()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF extraction failed: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/search-within")
async def search_within_pdf(
    file: UploadFile = File(...),
    query: str = "",
):
    """
    Upload a PDF and search for a query term within its text.
    Returns matching excerpts with context.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        from document.pdf_reader import read_pdf
        text = read_pdf(tmp_path)

        excerpts = []
        if query:
            lower_text = text.lower()
            lower_query = query.lower()
            pos = 0
            while True:
                idx = lower_text.find(lower_query, pos)
                if idx == -1:
                    break
                start = max(0, idx - 100)
                end   = min(len(text), idx + len(query) + 100)
                excerpts.append({
                    "position": idx,
                    "excerpt":  text[start:end],
                })
                pos = idx + 1
                if len(excerpts) >= 10:
                    break

        return {
            "filename": file.filename,
            "query":    query,
            "matches":  len(excerpts),
            "excerpts": excerpts,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


