# ðŸ“ LOCATION: backend/app/routes/import_routes.py
"""
import_routes.py
================
Bulk import API endpoints â€” import entire directories,
check for duplicates, preview unimported files.
"""

from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/import", tags=["import"])


class ImportRequest(BaseModel):
    directory:  str
    recursive:  bool = False
    dry_run:    bool = False
    skip_existing: bool = True


class DuplicateDeleteRequest(BaseModel):
    keep_id:   int
    delete_id: int


@router.post("/directory")
def import_directory(payload: ImportRequest, background_tasks: BackgroundTasks):
    """
    Import all supported files from a given directory.
    Use dry_run=true to preview what would be imported without saving.
    """
    if payload.dry_run:
        from app.services.auto_importer import import_directory as _import
        result = _import(
            payload.directory,
            recursive=payload.recursive,
            dry_run=True,
            skip_existing=payload.skip_existing,
        )
        return {"dry_run": True, "preview": result}

    background_tasks.add_task(
        _run_import,
        payload.directory,
        payload.recursive,
        payload.skip_existing,
    )
    return {"message": f"Import started for: {payload.directory}. Check /stats for progress."}


@router.get("/preview")
def preview_directory(
    directory: str = Query(...),
    recursive: bool = Query(False),
):
    """Preview what files would be imported from a directory."""
    from app.services.auto_importer import import_directory
    result = import_directory(directory, recursive=recursive, dry_run=True)
    return result


@router.get("/duplicates")
def get_duplicates():
    """Scan all memories for near-duplicates."""
    from database.database import SessionLocal
    from app.services.duplicate_service import find_all_duplicates
    db = SessionLocal()
    try:
        return find_all_duplicates(db)
    finally:
        db.close()


@router.delete("/duplicate")
def delete_duplicate(payload: DuplicateDeleteRequest):
    """Delete a duplicate memory, keeping the preferred one."""
    from database.database import SessionLocal
    from app.services.duplicate_service import delete_duplicate as _delete
    db = SessionLocal()
    try:
        ok = _delete(db, payload.keep_id, payload.delete_id)
        if ok:
            # âœ… Refresh cache and rebuild indices after duplicate deletion
            _refresh_after_change()
            return {"message": f"Memory {payload.delete_id} deleted, kept {payload.keep_id}"}
        return {"error": "Memory not found"}
    finally:
        db.close()


def _run_import(directory: str, recursive: bool, skip_existing: bool):
    """
    Background task for running the actual import.
    After completion, refresh cache and rebuild indices.
    """
    from app.services.auto_importer import import_directory
    result = import_directory(directory, recursive=recursive, skip_existing=skip_existing)
    print(f"[Import] Completed: {result}")
    
    # âœ… Refresh cache and rebuild indices after successful import
    if result and result.get("imported", 0) > 0:
        _refresh_after_change()
        print(f"[Import] Cache and indices refreshed after importing {result['imported']} files")


def _refresh_after_change():
    """
    Common function to refresh memory cache and rebuild search indices
    after any data modification.
    """
    try:
        from app.services.database_service import refresh_memory_cache, get_all_memories
        from ai.faiss_service import build_index
        from ai.hybrid_search import build_bm25
        
        # Refresh in-memory cache
        refresh_memory_cache()
        print("[Import] Memory cache refreshed")
        
        # Rebuild FAISS and BM25 indices
        memories = get_all_memories()
        if memories:
            build_index(memories)
            print(f"[Import] FAISS index rebuilt with {len(memories)} memories")
            
            build_bm25(memories)
            print(f"[Import] BM25 index rebuilt with {len(memories)} memories")
        else:
            print("[Import] No memories to index")
    except Exception as e:
        print(f"[Import] Error refreshing after change: {e}")


