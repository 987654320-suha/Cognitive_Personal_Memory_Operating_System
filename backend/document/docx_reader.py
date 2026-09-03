"""
document/docx_reader.py
========================
Extracts text from Word documents using python-docx.
"""

from __future__ import annotations


def read_docx(file_path: str) -> str:
    try:
        from docx import Document
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs).strip()
    except ImportError:
        print("[DOCXReader] python-docx not installed.")
        return ""
    except Exception as e:
        print(f"[DOCXReader] Error on {file_path}: {e}")
        return ""
