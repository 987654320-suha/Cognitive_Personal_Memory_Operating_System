"""
ai/summarizer.py
================

CogniSphere local document summarizer.

Uses Ollama with phi3:mini for short summaries.

The model is kept alive between requests to avoid repeated
cold-start loading.

If Ollama is unavailable or times out, the function falls back
to a cleaned excerpt of the document text.
"""

from __future__ import annotations

import os
import re
import requests


# ============================================================================
# Ollama / LLM Configuration
# ============================================================================

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_URL = os.getenv("OLLAMA_URL", f"{OLLAMA_BASE_URL}/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")

# Keep model loaded between summarization requests.
OLLAMA_KEEP_ALIVE = "30m"

# Maximum generated tokens.
NUM_PREDICT = 60

# Maximum input sent to Ollama.
MAX_INPUT_CHARS = 2000

# Maximum summary length stored/displayed.
SUMMARY_MAX_CHARS = 300

# Connect & read timeouts for local Ollama.
# Fast connection timeout (1.0s) prevents freezing the server when Ollama is offline (e.g. on Render).
OLLAMA_CONNECT_TIMEOUT = float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "1.0"))
OLLAMA_READ_TIMEOUT = float(os.getenv("OLLAMA_READ_TIMEOUT", "6.0"))

# In-memory availability cache: avoids repeatedly attempting sockets when offline
_ollama_status_cache = {"available": None, "last_checked": 0.0}

SUMMARY_PROMPT = """
Summarize the following document content in 1-2 concise sentences.

Rules:
- Be factual.
- Do not invent information.
- Do not add a preamble.
- Focus on the main topic and important details.
- Return only the summary.

Document content:

{text}

Summary:
""".strip()


# ============================================================================
# Summary Generation
# ============================================================================

def generate_summary(
    text: str,
    max_input_chars: int = MAX_INPUT_CHARS,
) -> str:
    """
    Generate a short summary using local Ollama.

    Parameters
    ----------
    text:
        Extracted document text.

    max_input_chars:
        Maximum number of document characters sent to Ollama.

    Returns
    -------
    str
        Generated summary.

    If Ollama is unavailable, a cleaned excerpt is returned instead.
    """

    # ------------------------------------------------------------------------
    # Empty / very short text
    # ------------------------------------------------------------------------

    if not text:
        return ""

    text = str(text).strip()

    if not text:
        return ""

    if len(text) < 50:
        return _clean_text(text)[:SUMMARY_MAX_CHARS]

    # ------------------------------------------------------------------------
    # Limit input size
    # ------------------------------------------------------------------------

    truncated = text[:max_input_chars].strip()

    # Skip Ollama call if explicitly disabled via environment
    if os.getenv("OLLAMA_ENABLED", "auto").lower() in ("false", "0", "no"):
        return _clean_text(truncated)[:SUMMARY_MAX_CHARS]

    # If recent check showed Ollama is offline (within last 120s), return fallback instantly
    import time
    now = time.time()
    if _ollama_status_cache["available"] is False and (now - _ollama_status_cache["last_checked"]) < 120.0:
        return _clean_text(truncated)[:SUMMARY_MAX_CHARS]

    prompt = SUMMARY_PROMPT.format(
        text=truncated
    )

    # ------------------------------------------------------------------------
    # Call Ollama with fast connect timeout
    # ------------------------------------------------------------------------

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "keep_alive": OLLAMA_KEEP_ALIVE,
                "options": {
                    "num_predict": NUM_PREDICT,
                    "temperature": 0.2,
                    "top_k": 20,
                    "top_p": 0.9,
                },
            },
            timeout=(OLLAMA_CONNECT_TIMEOUT, OLLAMA_READ_TIMEOUT),
        )

        if response.status_code == 200:
            _ollama_status_cache["available"] = True
            _ollama_status_cache["last_checked"] = now
            data = response.json()
            summary = (data.get("response") or "").strip()
            summary = _clean_text(summary)
            if summary:
                return summary[:SUMMARY_MAX_CHARS]
        else:
            print(f"[Summarizer] Ollama returned HTTP {response.status_code}. Using fallback.")

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        _ollama_status_cache["available"] = False
        _ollama_status_cache["last_checked"] = now
        print(f"[Summarizer] Ollama unavailable ({type(e).__name__}). Using fast text excerpt.")

    except Exception as e:
        _ollama_status_cache["available"] = False
        _ollama_status_cache["last_checked"] = now
        print(f"[Summarizer] Error calling Ollama ({e}). Using fast fallback.")

    return _clean_text(truncated)[:SUMMARY_MAX_CHARS]


# ============================================================================
# Text Cleaning
# ============================================================================

def _clean_text(text: str) -> str:
    """
    Normalize whitespace so summaries remain compact.
    """

    if not text:
        return ""

    text = re.sub(
        r"\s+",
        " ",
        str(text),
    )

    return text.strip()


