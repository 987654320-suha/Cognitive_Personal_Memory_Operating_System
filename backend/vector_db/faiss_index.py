"""
vector_db/faiss_index.py
========================
Persistent FAISS index wrapper.
Saves and loads index to disk so it survives server restarts.
"""

from __future__ import annotations
import os
import json
import numpy as np
from pathlib import Path

INDEX_PATH    = Path("vector_db/faiss.index")
METADATA_PATH = Path("vector_db/faiss_meta.json")

_index = None
_meta: list[dict] = []


def save_index():
    global _index, _meta
    if _index is None:
        return
    try:
        import faiss
        INDEX_PATH.parent.mkdir(exist_ok=True)
        faiss.write_index(_index, str(INDEX_PATH))
        METADATA_PATH.write_text(json.dumps(_meta))
        print(f"[FAISS] Index saved ({len(_meta)} vectors).")
    except Exception as e:
        print(f"[FAISS] Save error: {e}")


def load_index() -> bool:
    global _index, _meta
    try:
        import faiss
        if INDEX_PATH.exists() and METADATA_PATH.exists():
            _index = faiss.read_index(str(INDEX_PATH))
            _meta  = json.loads(METADATA_PATH.read_text())
            print(f"[FAISS] Index loaded ({len(_meta)} vectors).")
            return True
    except Exception as e:
        print(f"[FAISS] Load error: {e}")
    return False
