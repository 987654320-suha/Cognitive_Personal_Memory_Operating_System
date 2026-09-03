"""
ai/goal_detector.py
===================
Two-tier goal detection:
  Tier 1 (fast): regex patterns in gama_service.detect_goals_from_text()
  Tier 2 (smart): Ollama LLM for ambiguous cases

This module handles Tier 2 and is only called when Tier 1 returns nothing.
"""

import os
import requests
import json
import re

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_URL = os.getenv("OLLAMA_URL", f"{OLLAMA_BASE_URL}/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

GOAL_PROMPT = """
You are an AI that categorizes personal documents into life goals.
Given the following text, identify which life goals it relates to.
Choose ONLY from these categories:
- Germany Masters
- Career
- Certifications
- Projects
- Travel / Visa
- Finance
- Health
- Education
- Personal

Return ONLY a JSON array of matching category names, e.g. ["Career", "Certifications"]
If nothing matches, return [].

Text:
{text}

JSON array:
"""


def detect_goals(text: str) -> list[str]:
    """
    First tries fast regex (gama_service), then falls back to Ollama LLM.
    """
    from ai.gama_service import detect_goals_from_text
    fast = detect_goals_from_text(text)
    if fast:
        return fast

    # LLM fallback for unusual documents
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": GOAL_PROMPT.format(text=text[:1500]),
                "stream": False,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            raw = resp.json().get("response", "").strip()
            # Extract JSON array from response
            match = re.search(r"\[.*?\]", raw, re.DOTALL)
            if match:
                return json.loads(match.group())
    except Exception as e:
        print(f"[GoalDetector] Ollama error: {e}")

    return []


