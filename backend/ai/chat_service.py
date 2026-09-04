"""
ai/chat_service.py
==================

CogniSphere RAG Chat Service
-----------------------------

Pipeline:

    User Query
        â†“
    ACMA Retrieval
        â†“
    Context Builder
        â†“
    Planner
        â†“
    Evidence / Explainability
        â†“
    Ollama (phi3:mini)
        â†“
    Final Answer

Design goals:
    - Use only retrieved CogniSphere memories as factual context.
    - Preserve ACMA ranking and explainability.
    - Keep Ollama warm to reduce cold-start latency.
    - Keep prompts compact enough for local CPU inference.
    - Provide useful evidence to the LLM.
    - Fail gracefully when Ollama is unavailable.
"""

from __future__ import annotations

import os
import time
from typing import List, Dict, Any

import requests
from sqlalchemy.orm import Session

from ai.semantic_search import acma_search
from ai.query_intent import detect_intent
from ai.context_builder import build_context
from ai.planner_service import build_plan


# ============================================================================
# Ollama / LLM Configuration
# ============================================================================

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_URL = os.getenv("OLLAMA_URL", f"{OLLAMA_BASE_URL}/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")

# Keep phi3:mini loaded in memory between requests.
OLLAMA_KEEP_ALIVE = -1

# Maximum characters of compressed section text sent to Ollama.
# Approximately 2,000â€“3,000 chars provides full section coverage
# while keeping CPU inference fast (<30 sec).
MAX_CONTEXT_CHARS = 2200

# Sufficient tokens for a concise, useful 2-4 sentence project summary on CPU.
NUM_PREDICT = 30

# Hard timeout for the LLM call.
OLLAMA_TIMEOUT = 60

# ============================================================================
# System Prompt
# ============================================================================

SYSTEM_PROMPT = """
You are CogniSphere, a personal memory assistant.

Answer the user's question using ONLY the retrieved memory context below.
Do not invent facts.
Do not mention that you are an AI model unless necessary.
Give a concise but useful answer.
If the user asks about a project, summarize:
1. What the project is
2. Problem it solves
3. Main objectives
4. Proposed approach/methodology
5. Important technologies/components
6. Expected result/innovation
""".strip()


# ============================================================================
# Memory Expansion
# ============================================================================

def expand_memories(
    db: Session,
    memories: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Expand retrieved memories with additional context if needed.

    Currently this intentionally returns the ACMA results unchanged.

    This function is kept as an extension point for future features such as:
        - parent/child memories
        - graph relationships
        - related documents
        - temporal neighbors
        - goal-linked memories
    """
    return memories


# ============================================================================
# Explainability / Evidence
# ============================================================================

def build_evidence(
    memories: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build an explainability trace showing which memories contributed
    to the answer.
    """

    evidence: List[Dict[str, Any]] = []

    for mem in memories:
        # Different parts of the pipeline may use different field names.
        content = (
            mem.get("content")
            or mem.get("description")
            or mem.get("text_content")
            or ""
        )

        evidence.append(
            {
                "memory_id": mem.get("id"),
                "content_preview": content[:200],
                "relevance_score": mem.get(
                    "confidence",
                    mem.get("score", 0),
                ),
                "source": mem.get("source", "unknown"),
                "timestamp": mem.get(
                    "created_at",
                    mem.get("date"),
                ),
            }
        )

    return evidence


# ============================================================================
# Memory Snippet Builder
# ============================================================================

def _extract_rag_context(mem: Dict[str, Any]) -> str:
    """
    Extract a compact, section-based RAG context from one memory.

    Strategy:
    1. Normalize PDF whitespace artifacts.
    2. Skip cover-page / TOC region (first ~5500 chars or past the last
       TOC-style line), which avoids matching headings that appear in the
       table of contents.
    3. Search the document body for both spaced headings ("Problem Statement")
       and run-together CamelCase headings ("ProblemStatement") using inline
       regex patterns.
    4. Extract content between adjacent section matches.
    5. Build a compressed context capped at MAX_CONTEXT_CHARS.

    Raw PDF text is NEVER forwarded to the frontend or LLM directly.
    """
    import re

    title = (mem.get("title") or "Untitled").strip()
    source = (mem.get("source") or "Unknown source").strip()
    text = str(mem.get("text_content") or mem.get("description") or "").strip()

    if not text:
        desc = str(mem.get("description") or "").strip()[:800]
        return f"Title: {title}\nSource: {source}\n{desc}"

    # ------------------------------------------------------------------
    # 1. Normalize
    # ------------------------------------------------------------------
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"\.{3,}", " ", text)          # dot leaders
    text = re.sub(r"(?m)^\s*\d{1,3}\s*$", " ", text)  # page numbers
    text = re.sub(r"[ \t]+", " ", text)

    # ------------------------------------------------------------------
    # 2. Skip TOC / cover-page region
    #
    # Find the last line that looks like a TOC entry:
    #   "SomeHeading  20"  or "3.2 SomeThing 20"
    # then start searching from after that line.
    # Fall back to a fixed offset if no TOC pattern is found.
    # ------------------------------------------------------------------
    toc_pattern = re.compile(
        r"(?m)^\s*(?:\d+\.)?\s*[A-Za-z][A-Za-z\s/,()-]{3,60}\s+\d{1,3}\s*$"
    )
    toc_end = 0
    for m in toc_pattern.finditer(text):
        toc_end = m.end()

    # Take the larger of heuristic and detected TOC end; cap at 12 000
    body_start = min(max(toc_end, 5000), 12000)
    body = text[body_start:]

    # ------------------------------------------------------------------
    # 3. Section definitions
    #    Each tuple: (label, [exact_phrases], inline_regex)
    #    We search body with both exact (multiline) and inline patterns.
    # ------------------------------------------------------------------
    SECTION_DEFS = [
        ("Abstract",
         ["ABSTRACT"],
         r"\bAbstract\b"),
        ("Problem Statement",
         ["PROBLEM STATEMENT", "PROBLEM DEFINITION"],
         r"\bProblem\s*(?:Statement|Definition)\b|ProblemStatement\b|ProblemDefinition\b"),
        ("Objectives",
         ["OBJECTIVES OF THE PROJECT", "OBJECTIVES", "OBJECTIVE"],
         r"\bObjectives?\s*(?:of\s*(?:the\s*)?[Pp]roject)?\b|ObjectivesoftheProject\b"),
        ("Scope",
         ["SCOPE OF THE PROJECT", "SCOPE"],
         r"\bScope\s*(?:of\s*(?:the\s*)?[Pp]roject)?\b|ScopeoftheProject\b"),
        ("Proposed Methodology",
         ["PROPOSED METHODOLOGY", "PROPOSED SYSTEM", "PROPOSED SOLUTION",
          "OVERVIEW OF PROPOSED WORK"],
         r"\bProposed\s*(?:Methodology|System|Solution|Work)\b"
         r"|ProposedMethodology\b|OverviewofProposedWork\b"),
        ("Architecture",
         ["SYSTEM ARCHITECTURE", "ARCHITECTURE"],
         r"\bSystem\s*Architecture\b|SystemArchitecture\b"),
        ("Technologies",
         ["SOFTWARE REQUIREMENTS", "TECHNOLOGIES USED",
          "TECHNOLOGY STACK", "TOOLS AND TECHNOLOGIES"],
         r"\bSoftware\s*Requirements?\b|Technolog(?:ies\s*Used|y\s*Stack)\b"
         r"|SoftwareRequirements\b|ToolsandTechnologies\b"),
        ("Expected Results",
         ["EXPECTED RESULTS", "EXPECTED OUTCOME"],
         r"\bExpected\s*(?:Results?|Outcome)\b|ExpectedOutcome\b"),
        ("Innovation",
         ["INNOVATION", "NOVELTY", "INNOVATION/NOVELTY"],
         r"\bInnovation(?:\s*/\s*Novelty)?\b|Novelty\b"),
        ("Future Scope",
         ["FUTURE SCOPE", "FUTURE ENHANCEMENTS"],
         r"\bFuture\s*(?:Scope|Enhancements?)\b|FutureScope\b"),
        ("Conclusion",
         ["CONCLUSION"],
         r"\bConclusion\b"),
    ]

    def find_in_body(search_text: str, exact_aliases: list, inline_pat: str):
        """
        Return the match that starts earliest in search_text.
        Tries exact multiline patterns first, then inline.
        """
        best = None
        # Exact on-its-own-line match
        for alias in exact_aliases:
            for m in re.finditer(
                rf"(?im)^\s*{re.escape(alias)}\s*:?\s*$",
                search_text,
            ):
                if best is None or m.start() < best.start():
                    best = m
        # Inline pattern
        m = re.search(inline_pat, search_text)
        if m and (best is None or m.start() < best.start()):
            best = m
        return best

    # ------------------------------------------------------------------
    # 4. Collect all section matches with their positions in `body`
    # ------------------------------------------------------------------
    matches = []  # [(start, end, label)]

    for label, exact_aliases, inline_pat in SECTION_DEFS:
        m = find_in_body(body, exact_aliases, inline_pat)
        if m:
            matches.append((m.start(), m.end(), label))

    # Sort by position in body
    matches.sort(key=lambda x: x[0])

    # ------------------------------------------------------------------
    # 5. Extract content between adjacent matches
    # ------------------------------------------------------------------
    extracted = []  # [(label, content)]
    seen_labels: set = set()

    for i, (mstart, mend, label) in enumerate(matches):
        if label in seen_labels:
            continue
        seen_labels.add(label)

        next_start = matches[i + 1][0] if i + 1 < len(matches) else len(body)
        raw = body[mend:next_start]
        content = re.sub(r"\s+", " ", raw).strip()

        # Discard tiny or obviously noisy sections
        if len(content) >= 80:
            extracted.append((label, content))

    # ------------------------------------------------------------------
    # 6. Build compressed context
    # ------------------------------------------------------------------
    SECTION_BUDGET = {
        "Abstract":             260,
        "Problem Statement":    240,
        "Objectives":           240,
        "Proposed Methodology": 220,
        "Technologies":         200,
        "Expected Results":     200,
        "Innovation":           160,
        "Architecture":         150,
        "Scope":                120,
        "Future Scope":         120,
        "Conclusion":           120,
    }

    parts: List[str] = [f"Title: {title}", f"Source: {source}"]
    used = 0
    budget = MAX_CONTEXT_CHARS - len(title) - len(source) - 30

    for label, content in extracted:
        if used >= budget:
            break
        alloc = min(SECTION_BUDGET.get(label, 200), budget - used)
        snippet = content[:alloc]
        # Trim to last sentence boundary
        last_stop = max(snippet.rfind(". "), snippet.rfind("! "), snippet.rfind("? "))
        if last_stop > alloc * 0.5:
            snippet = snippet[:last_stop + 1]
        parts.append(f"\n[{label}]\n{snippet}")
        used += len(snippet)

    # ------------------------------------------------------------------
    # 7. Fallback: no sections found â†’ use first 1000 chars of body
    # ------------------------------------------------------------------
    if len(parts) <= 2:
        desc = str(mem.get("description") or "").strip()
        if desc:
            parts.append(desc[:600])
        else:
            parts.append(body[:1000])

    return "\n".join(parts)


def _build_memory_snippet(
    mem: Dict[str, Any],
) -> str:
    """
    Convert one retrieved memory into a compact, useful RAG snippet.

    For memories that have text_content (e.g. PDF documents), this calls
    _extract_rag_context which compresses the full PDF text down to the
    most relevant sections.

    For memories without text_content, it falls back to description.
    """

    text_content = mem.get("text_content") or ""

    if str(text_content).strip():
        # Use the section extractor for document memories.
        return _extract_rag_context(mem)

    # Plain memory (no document text): use description.
    title = mem.get("title") or "Untitled"
    source = mem.get("source") or "Unknown"
    file_type = mem.get("file_type") or "Unknown"

    description = (
        mem.get("description")
        or mem.get("content")
        or ""
    )
    description = str(description).strip()[:500]

    return (
        f"Title: {title}\n"
        f"File: {source}\n"
        f"Type: {file_type}\n"
        f"Description: {description}"
    )


def _build_memory_context(
    memories: List[Dict[str, Any]],
) -> str:
    """
    Build the final memory context sent to Ollama.

    Each memory is compressed by _build_memory_snippet / _extract_rag_context.
    De-duplicates identical documents (e.g. Yorai (1) and Yorai (2)) to keep
    the prompt compact for fast LLM inference.
    """

    snippets = []
    seen_bases = set()

    for mem in memories:
        title = (mem.get("title") or "").strip()
        source = (mem.get("source") or "").strip()
        # Key on base filename/title to avoid sending 2 duplicate copies of the same PDF
        import re
        base_key = re.sub(r"\s*\(\d+\)", "", (source or title)).lower().strip()
        
        if base_key and base_key in seen_bases and len(memories) > 1:
            continue
        
        seen_bases.add(base_key)
        snippets.append(_build_memory_snippet(mem))

    context = "\n\n--- MEMORY ---\n\n".join(snippets)

    if len(context) > MAX_CONTEXT_CHARS:
        context = (
            context[:MAX_CONTEXT_CHARS]
            + "\n...[context trimmed]"
        )

    return context


# ============================================================================
# ============================================================================
# Ollama Call
# ============================================================================

def _call_ollama(prompt: str) -> tuple[str, float]:
    """
    Call Ollama and return:

        (answer, elapsed_seconds)

    Raises:
        requests.exceptions.ConnectionError
        requests.exceptions.Timeout
        requests.exceptions.RequestException
    """

    start = time.time()

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,

        # Keep phi3:mini loaded between requests.
        "keep_alive": OLLAMA_KEEP_ALIVE,

        "options": {
            # Allow enough tokens for a useful project summary.
            "num_predict": NUM_PREDICT,

            # Slightly creative for readable prose but still factual.
            "temperature": 0.2,

            # Standard sampling.
            "top_k": 40,
            "top_p": 0.9,
        },
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=OLLAMA_TIMEOUT,
    )

    elapsed = time.time() - start

    response.raise_for_status()

    data = response.json()

    answer = (
        data.get("response") or ""
    ).strip()

    return answer, elapsed


# ============================================================================
# Fast Memory Answer
# ============================================================================
def _build_fast_memory_answer(query: str, memories: list[dict]) -> str:
    """
    Fast structured summarization of an already-identified memory.

    IMPORTANT:
    - Does NOT call Ollama.
    - Does NOT send the entire document to the frontend.
    - Uses the stored text_content as the source.
    - Extracts important project/document sections.
    - Produces a concise deterministic summary.
    """

    import re

    if not memories:
        return "I couldn't find a relevant memory for that question."

    # ------------------------------------------------------------
    # 1. Select strongest memory
    # ------------------------------------------------------------

    mem = memories[0]

    title = (mem.get("title") or "Untitled").strip()
    source = (mem.get("source") or "Unknown source").strip()

    text = (
        mem.get("text_content")
        or mem.get("description")
        or ""
    )

    text = str(text).strip()

    if not text:
        return (
            f"I found **{title}**, but there is no detailed "
            f"content available for this memory."
        )

    # ------------------------------------------------------------
    # 2. Normalize PDF text
    # ------------------------------------------------------------

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove dot leaders / table-of-contents noise
    text = re.sub(r"\.{3,}", " ", text)

    # Remove page-number-like sequences
    text = re.sub(r"\s+\d{1,3}\s+", " ", text)

    # Fix excessive spaces
    text = re.sub(r"[ \t]+", " ", text)

    # ------------------------------------------------------------
    # 3. Define important sections
    # ------------------------------------------------------------

    section_aliases = {
        "Abstract": [
            "ABSTRACT",
        ],

        "Problem Statement": [
            "PROBLEM STATEMENT",
            "PROBLEM DEFINITION",
        ],

        "Objectives": [
            "OBJECTIVES OF THE PROJECT",
            "OBJECTIVES",
            "OBJECTIVE",
        ],

        "Scope": [
            "SCOPE OF THE PROJECT",
            "SCOPE",
        ],

        "Proposed Methodology": [
            "PROPOSED METHODOLOGY",
            "PROPOSED SYSTEM",
            "PROPOSED SOLUTION",
        ],

        "Architecture": [
            "SYSTEM ARCHITECTURE",
            "ARCHITECTURE",
        ],

        "Technologies": [
            "SOFTWARE REQUIREMENTS",
            "TECHNOLOGIES USED",
            "TECHNOLOGY STACK",
            "TOOLS AND TECHNOLOGIES",
        ],

        "Expected Results": [
            "EXPECTED RESULTS",
            "EXPECTED OUTCOME",
        ],

        "Innovation": [
            "INNOVATION",
            "NOVELTY",
        ],

        "Conclusion": [
            "CONCLUSION",
        ],

        "Future Scope": [
            "FUTURE SCOPE",
        ],
    }

    # ------------------------------------------------------------
    # 4. Extract sections
    # ------------------------------------------------------------

    sections = {}

    for section_name, aliases in section_aliases.items():

        start_match = None

        for alias in aliases:

            match = re.search(
                rf"(?im)^\s*{re.escape(alias)}\s*:?\s*$",
                text,
            )

            if match:
                start_match = match
                break

        if not start_match:
            continue

        start = start_match.end()

        # Find next likely numbered section or uppercase heading.
        next_match = re.search(
            r"""
            (?im)
            ^
            \s*
            (?:
                \d+(?:\.\d+)*\s+
            )?
            [A-Z][A-Z\s/&\-]{4,70}
            \s*:?
            \s*$
            """,
            text[start:],
            flags=re.VERBOSE,
        )

        if next_match:
            end = start + next_match.start()
        else:
            end = min(start + 6000, len(text))

        content = text[start:end].strip()

        # Normalize
        content = re.sub(r"\s+", " ", content).strip()

        # Ignore tiny sections
        if len(content) >= 80:
            sections[section_name] = content

    # ------------------------------------------------------------
    # 5. Sentence extraction helper
    # ------------------------------------------------------------

    def sentences(value: str) -> list[str]:

        value = re.sub(r"\s+", " ", value).strip()

        parts = re.split(
            r"(?<=[.!?])\s+",
            value,
        )

        result = []

        for sentence in parts:

            sentence = sentence.strip()

            # Ignore very short fragments
            if len(sentence) < 45:
                continue

            # Ignore obvious TOC fragments
            if "." * 3 in sentence:
                continue

            # Ignore page-number-heavy fragments
            if len(re.findall(r"\d+", sentence)) > 8:
                continue

            result.append(sentence)

        return result

    # ------------------------------------------------------------
    # 6. Select useful sentences
    # ------------------------------------------------------------

    def summarize_section(
        content: str,
        max_sentences: int = 2,
        max_chars: int = 500,
    ) -> str:

        sents = sentences(content)

        if not sents:
            return content[:max_chars].strip()

        # Prefer sentences containing meaningful project terms.
        keywords = [
            "yorai",
            "project",
            "system",
            "platform",
            "security",
            "browser",
            "ai",
            "artificial intelligence",
            "detect",
            "prevent",
            "protect",
            "threat",
            "phishing",
            "malicious",
            "attack",
            "user",
            "privacy",
            "authentication",
        ]

        scored = []

        for index, sentence in enumerate(sents):

            lower = sentence.lower()

            score = 0

            for keyword in keywords:
                if keyword in lower:
                    score += 1

            # Slight preference for earlier sentences.
            score += max(
                0,
                2 - (index * 0.05)
            )

            scored.append(
                (score, index, sentence)
            )

        scored.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        selected = sorted(
            scored[:max_sentences],
            key=lambda x: x[1],
        )

        result = " ".join(
            item[2]
            for item in selected
        )

        if len(result) > max_chars:
            result = (
                result[:max_chars]
                .rsplit(" ", 1)[0]
                + "..."
            )

        return result

    # ------------------------------------------------------------
    # 7. Build concise project summary
    # ------------------------------------------------------------

    output = []

    output.append(f"### {title}")
    output.append("")

    # Abstract / overview
    if "Abstract" in sections:

        summary = summarize_section(
            sections["Abstract"],
            max_sentences=2,
            max_chars=650,
        )

        output.append("**Overview**")
        output.append(summary)
        output.append("")

    # Problem
    if "Problem Statement" in sections:

        summary = summarize_section(
            sections["Problem Statement"],
            max_sentences=2,
            max_chars=500,
        )

        output.append("**Problem Addressed**")
        output.append(summary)
        output.append("")

    # Objectives
    if "Objectives" in sections:

        summary = summarize_section(
            sections["Objectives"],
            max_sentences=2,
            max_chars=500,
        )

        output.append("**Main Objectives**")
        output.append(summary)
        output.append("")

    # Methodology
    if "Proposed Methodology" in sections:

        summary = summarize_section(
            sections["Proposed Methodology"],
            max_sentences=2,
            max_chars=550,
        )

        output.append("**Proposed Approach**")
        output.append(summary)
        output.append("")

    # Architecture
    if "Architecture" in sections:

        summary = summarize_section(
            sections["Architecture"],
            max_sentences=2,
            max_chars=450,
        )

        output.append("**Architecture**")
        output.append(summary)
        output.append("")

    # Technologies
    if "Technologies" in sections:

        summary = summarize_section(
            sections["Technologies"],
            max_sentences=2,
            max_chars=450,
        )

        output.append("**Technologies / Requirements**")
        output.append(summary)
        output.append("")

    # Innovation
    if "Innovation" in sections:

        summary = summarize_section(
            sections["Innovation"],
            max_sentences=2,
            max_chars=450,
        )

        output.append("**Innovation / Novelty**")
        output.append(summary)
        output.append("")

    # Expected results
    if "Expected Results" in sections:

        summary = summarize_section(
            sections["Expected Results"],
            max_sentences=2,
            max_chars=450,
        )

        output.append("**Expected Results**")
        output.append(summary)
        output.append("")

    # Future scope
    if "Future Scope" in sections:

        summary = summarize_section(
            sections["Future Scope"],
            max_sentences=2,
            max_chars=450,
        )

        output.append("**Future Scope**")
        output.append(summary)
        output.append("")

    # ------------------------------------------------------------
    # 8. Fallback
    # ------------------------------------------------------------

    if len(output) <= 3:

        fallback_sentences = sentences(text)

        useful = fallback_sentences[:6]

        if useful:

            output.append("**Summary**")
            output.append(
                " ".join(useful)[:3000]
            )

    output.append(
        f"**Source:** {source}"
    )

    return "\n".join(output)

# ============================================================================
# Simple Memory Query Detection
# ============================================================================

def _is_simple_memory_query(query: str) -> bool:
    """
    Detect questions that can be answered directly from memory
    without LLM synthesis.
    """

    q = query.lower().strip()

    complex_terms = [
        "compare",
        "comparison",
        "difference",
        "differences",
        "versus",
        " vs ",
        "which is better",
        "analyze",
        "analyse",
        "evaluate",
        "recommend",
    ]

    if any(term in q for term in complex_terms):
        return False

    simple_patterns = [
        "tell me about",
        "what is",
        "what's",
        "give me information about",
        "give me details about",
        "describe",
        "overview of",
        "summary of",
        "explain my",
    ]

    return any(pattern in q for pattern in simple_patterns)


# ============================================================================
# Main Chat Function
# ============================================================================

def chat_with_memories(
    query: str,
    db: Session,
    conversation_history: list[dict] | None = None,
    user_id: int | None = None,
) -> dict:
    """
    Execute the CogniSphere RAG chat pipeline.

    Returns:

        {
            "answer": str,
            "intent": str,
            "confidence": float,
            "memories_used": list,
            "goal_context": list,
            "sources": list,
            "plan": dict
        }
    """

    t0 = time.time()

    print("=" * 70)
    print("CHAT REQUEST RECEIVED")
    print("Query:", query)
    print("=" * 70)

    # ------------------------------------------------------------------------
    # 1. ACMA Retrieval
    # ------------------------------------------------------------------------

    retrieval_start = time.time()

    try:
        acma_results = acma_search(
            query=query,
            db=db,
            top_k=2,
            user_id=user_id,
        )
    except Exception as e:
        print("[Chat] ACMA search error:", e)

        return {
            "answer": (
                "I couldn't search your memory database because "
                "the retrieval system encountered an error."
            ),
            "intent": "unknown",
            "confidence": 0.0,
            "memories_used": [],
            "goal_context": [],
            "sources": [],
            "plan": {},
        }

    retrieval_time = time.time() - retrieval_start

    print("ACMA returned:", len(acma_results))
    print(
        "ACMA Search:",
        round(retrieval_time, 2),
        "sec",
    )

    # ================================================================
    # RAG CONTEXT PREPARATION
    # ================================================================
    #
    # When ACMA detects a strong memory match (e.g. "tell me about my
    # YORAI project"), we still call Ollama â€” but with a compressed
    # context extracted from the relevant document sections, not the
    # full 49k-char PDF.
    #
    # Logging uses [RAG] prefix (not [FAST ANSWER]).
    # ================================================================

    if acma_results and _is_simple_memory_query(query):
        print("[RAG] Strong memory match detected.")
        rag_context = _build_memory_context(acma_results)
        print(f"[RAG] Context prepared: {len(rag_context)} chars.")

    # ------------------------------------------------------------------------
    # 2. No memories found
    # ------------------------------------------------------------------------

    if not acma_results:
        print("[Chat] No relevant memories found.")

        return {
            "answer": (
                "I couldn't find any relevant memories. "
                "Try uploading related documents first."
            ),
            "intent": "unknown",
            "confidence": 0.0,
            "memories_used": [],
            "goal_context": [],
            "sources": [],
            "plan": {},
        }

    # ------------------------------------------------------------------------
    # 3. Expand Memories
    # ------------------------------------------------------------------------

    try:
        acma_results = expand_memories(
            db,
            acma_results,
        )
    except Exception as e:
        print("[Chat] Memory expansion error:", e)

    # ------------------------------------------------------------------------
    # 4. Intent + Context + Planner
    # ------------------------------------------------------------------------

    print("Building prompt...")

    context_start = time.time()

    try:
        intent = detect_intent(query)
    except Exception as e:
        print("[Chat] Intent detection error:", e)
        intent = "unknown"

    try:
        ctx = build_context(acma_results)
    except Exception as e:
        print("[Chat] Context builder error:", e)

        # Safe fallback context.
        ctx = {
            "context": "",
            "memories": acma_results,
            "goal_context": [],
        }

    try:
        plan = build_plan(
            query,
            ctx.get("memories", acma_results),
        )
    except Exception as e:
        print("[Chat] Planner error:", e)
        plan = {}

    context_time = time.time() - context_start

    print(
        "Context + Planner:",
        round(context_time, 2),
        "sec",
    )

    # ------------------------------------------------------------------------
    # 5. Extract Context
    # ------------------------------------------------------------------------

    memories_used = ctx.get(
        "memories",
        acma_results,
    )

    goal_context = ctx.get(
        "goal_context",
        [],
    )

    # ------------------------------------------------------------------------
    # 6. Evidence / Explainability
    # ------------------------------------------------------------------------

    evidence = build_evidence(
        memories_used
    )

    # ------------------------------------------------------------------------
    # 7. Build Compact RAG Context
    # ------------------------------------------------------------------------

    memory_context = _build_memory_context(
        memories_used
    )

    intent_value = (
        intent.value
        if hasattr(intent, "value")
        else str(intent)
    )

    prompt = f"""
{SYSTEM_PROMPT}

User question:
{query}

Retrieved memory context:
{memory_context}

Answer:
""".strip()

    print(
        "Prompt characters:",
        len(prompt),
    )

    # ------------------------------------------------------------------------
    # 8. Ollama Generation
    # ------------------------------------------------------------------------

    print(
        f"[RAG] Calling Ollama: {OLLAMA_MODEL}"
    )

    ollama_start = time.time()

    answer: str

    try:
        answer, ollama_time = _call_ollama(
            prompt
        )

        print(
            f"[RAG] Ollama generated answer in {round(ollama_time, 2)} sec."
        )

        if not answer:
            answer = (
                "Ollama returned an empty response. "
                "Please try again."
            )

    except requests.exceptions.Timeout:
        ollama_time = time.time() - ollama_start

        print(
            "Ollama TIMEOUT:",
            round(ollama_time, 2),
            "sec",
        )

        answer = (
            "The local AI model took too long to respond. "
            "Your memories were retrieved successfully, "
            "but Ollama did not finish generating the answer "
            "within the allowed time."
        )

    except requests.exceptions.ConnectionError:
        ollama_time = time.time() - ollama_start

        print(
            "Ollama CONNECTION ERROR:",
            round(ollama_time, 2),
            "sec",
        )

        answer = (
            "I retrieved your relevant memories, but I "
            "couldn't connect to Ollama. Please make sure "
            "Ollama is running on port 11434."
        )

    except requests.exceptions.RequestException as e:
        ollama_time = time.time() - ollama_start

        print(
            "Ollama REQUEST ERROR:",
            e,
        )

        answer = (
            "The local AI generation service returned an error. "
            "Please check Ollama and try again."
        )

    except Exception as e:
        ollama_time = time.time() - ollama_start

        print(
            "Ollama UNEXPECTED ERROR:",
            e,
        )

        answer = (
            "An unexpected error occurred while generating "
            "the AI response."
        )

    # ------------------------------------------------------------------------
    # 9. Confidence
    # ------------------------------------------------------------------------

    if memories_used:
        confidence_values = []

        for mem in memories_used:
            value = mem.get(
                "activation_score",
                mem.get(
                    "confidence",
                    mem.get(
                        "score",
                        0,
                    ),
                ),
            )

            try:
                val = float(value)
                # If score is on 0.0-1.0 scale, convert to percentage 0-100
                if 0.0 < val <= 1.0:
                    val = val * 100.0
                confidence_values.append(val)
            except (
                TypeError,
                ValueError,
            ):
                continue

        if confidence_values:
            confidence = round(
                sum(confidence_values)
                / len(confidence_values),
                1,
            )
        else:
            confidence = 90.0
    else:
        confidence = 0.0

    # ------------------------------------------------------------------------
    # 10. Total Timing
    # ------------------------------------------------------------------------

    total_time = time.time() - t0

    print("-" * 70)
    print(
        "CHAT COMPLETE"
    )
    print(
        "Retrieval:",
        round(retrieval_time, 2),
        "sec",
    )
    print(
        "Context:",
        round(context_time, 2),
        "sec",
    )
    print(
        "Ollama:",
        round(ollama_time, 2),
        "sec",
    )
    print(
        "TOTAL:",
        round(total_time, 2),
        "sec",
    )
    print("-" * 70)

    # ------------------------------------------------------------------------
    # 11. Final Response
    # ------------------------------------------------------------------------

    return {
        "answer": answer,

        "intent": intent_value,

        "confidence": confidence,

        "goal_context": goal_context,

        "sources": evidence,

        "memories_used": memories_used,

        "plan": plan,
    }


# ============================================================================
# Local Test
# ============================================================================

if __name__ == "__main__":

    from unittest.mock import MagicMock

    mock_db = MagicMock(
        spec=Session
    )

    test_query = (
        "What were my goals for this quarter?"
    )

    result = chat_with_memories(
        test_query,
        mock_db,
    )

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)

    print(
        "Answer:",
        result["answer"],
    )

    print(
        "Intent:",
        result["intent"],
    )

    print(
        "Confidence:",
        result["confidence"],
    )

    print(
        "Memories used:",
        len(result["memories_used"]),
    )

    print(
        "Goal context:",
        result["goal_context"],
    )

    print(
        "Sources:",
        len(result["sources"]),
    )


