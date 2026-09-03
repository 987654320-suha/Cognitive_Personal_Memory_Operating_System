# ðŸ“ LOCATION: backend/app/routes/index_routes.py
"""
index_routes.py
===============
FAISS index management endpoints â€” rebuild, status, persist.
Also exposes folder indexer endpoint to preview unindexed files.
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from database.database import get_db

router = APIRouter(prefix="/index", tags=["index"])


@router.get("/status")
def index_status():
    """Returns FAISS index statistics."""
    try:
        from ai.faiss_service import _indexed_memories, _index
        return {
            "indexed_memories": len(_indexed_memories),
            "index_ready": _index is not None,
        }
    except Exception as e:
        return {"error": str(e), "index_ready": False}


@router.post("/rebuild")
def rebuild_index(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Triggers a full FAISS index rebuild from the DB.
    Runs in the background so the API stays responsive.
    """
    background_tasks.add_task(_rebuild_task)
    return {"message": "Index rebuild started in background"}


@router.post("/save")
def save_index_to_disk():
    """Persists the current FAISS index to disk (vector_db/)."""
    try:
        from vector_db.faiss_index import save_index
        save_index()
        return {"message": "Index saved to disk"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/load")
def load_index_from_disk():
    """Loads a previously saved FAISS index from disk."""
    try:
        from vector_db.faiss_index import load_index
        ok = load_index()
        return {"message": "Index loaded" if ok else "No saved index found"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/unindexed-files")
def get_unindexed_files():
    """
    Returns files on disk that haven't been ingested into CogniSphere yet.
    Scans Desktop, Downloads, Documents, Pictures.
    """
    try:
        from app.services.folder_indexer import find_uningested_files
        files = find_uningested_files()
        return {"count": len(files), "files": files}
    except Exception as e:
        return {"error": str(e), "files": []}


@router.post("/import-unindexed")
def import_unindexed_files(background_tasks: BackgroundTasks):
    """
    Ingests all unindexed files from watched directories.
    Runs in background.
    """
    background_tasks.add_task(_import_unindexed_task)
    return {"message": "Import started in background. Check /stats for progress."}


# â”€â”€ Background tasks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _rebuild_task():
    try:
        from app.services.database_service import get_all_memories
        from ai.faiss_service import build_index
        memories = get_all_memories()
        build_index(memories)
        print(f"[Index] Rebuild complete: {len(memories)} memories indexed")
    except Exception as e:
        print(f"[Index] Rebuild error: {e}")


def _import_unindexed_task():
    """
    Import all unindexed files.

    Memories are saved to SQLite individually, but FAISS/BM25
    are rebuilt only once after the entire batch is complete.
    """
    try:
        from app.services.folder_indexer import find_uningested_files
        from ai.memory_pipeline import run_pipeline

        files = find_uningested_files()

        print(
            f"[Index] Importing {len(files)} unindexed files..."
        )

        successful = 0
        failed = 0

        for i, f in enumerate(files, start=1):
            try:
                print(
                    f"[Index] [{i}/{len(files)}] "
                    f"Processing: {f['name']}"
                )

                run_pipeline(
                    f["path"],
                    update_index=False,
                )

                successful += 1

                print(
                    f"[Index] [{i}/{len(files)}] "
                    f"Ingested: {f['name']}"
                )

            except Exception as e:
                failed += 1

                print(
                    f"[Index] [{i}/{len(files)}] "
                    f"ERROR: {f['name']}: {e}"
                )

        # =====================================================
        # FINAL CACHE + SEARCH INDEX REFRESH
        # =====================================================

        print("[Index] Import batch complete.")
        print(
            f"[Index] Successful: {successful}, "
            f"Failed: {failed}"
        )

        from app.services.database_service import (
            refresh_memory_cache,
            get_all_memories,
        )
        from ai.faiss_service import build_index
        from ai.hybrid_search import build_bm25
        from ai.semantic_search import invalidate_search_cache

        print("[Index] Refreshing memory cache...")

        refresh_memory_cache()

        memories = get_all_memories()

        print(
            f"[Index] Rebuilding FAISS with "
            f"{len(memories)} memories..."
        )

        build_index(memories)

        print(
            f"[Index] Rebuilding BM25 with "
            f"{len(memories)} memories..."
        )

        build_bm25(memories)

        invalidate_search_cache()

        print(
            f"[Index] FINAL: {len(memories)} memories "
            f"available for search."
        )

    except Exception as e:
        print(
            f"[Index] Import task error: {e}"
        )


