"""
document/pdf_reader.py
=======================
Extracts text from PDF files using pdfplumber.
"""

from __future__ import annotations


def read_pdf(file_path: str, max_pages: int = 30) -> str:
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= max_pages:
                    break
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                    if sum(len(p) for p in text_parts) > 30000:
                        break
        return "\n".join(text_parts).strip()
    except ImportError:
        print("[PDFReader] pdfplumber not installed.")
        return ""
    except Exception as e:
        print(f"[PDFReader] Error on {file_path}: {e}")
        return ""
