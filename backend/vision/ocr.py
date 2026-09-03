"""
vision/ocr.py
=============
OCR text extraction using pytesseract + Pillow.
"""

from __future__ import annotations


def extract_text(image_path: str) -> str:
    """Returns extracted text string or empty string on failure."""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except ImportError:
        print("[OCR] pytesseract or Pillow not installed.")
        return ""
    except Exception as e:
        print(f"[OCR] Error on {image_path}: {e}")
        return ""
