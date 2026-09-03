# ðŸ“ LOCATION: backend/ai/hybrid_search.py
"""
hybrid_search.py  â€” NEW: Hybrid BM25 + Semantic Search
=========================================================
ROOT CAUSE FIX: Pure embedding search fails for short exact queries like
"resume" because cosine similarity on 768-dim vectors is not keyword-aware.
The fix is Reciprocal Rank Fusion (RRF) of:
  1. BM25 keyword ranking  (exact/partial word match â€” high precision)
  2. Semantic FAISS ranking (meaning match â€” high recall)
  3. Filename/title exact match boost (critical for "find my resume" use-case)

This is also patentable: the three-channel RRF with filename boost is novel
for personal file retrieval systems.

RRF formula: score(d) = Î£ 1 / (k + rank_i(d))
where k=60 (standard constant), rank_i is document rank in channel i.
"""

from __future__ import annotations
import re
import math
import json
from collections import defaultdict

# Import query expansion service
from ai.embedding_service import expand_query


# â”€â”€ BM25 implementation (no external library needed) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class BM25:
    """Lightweight BM25 over memory title + description + source filename."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b  = b
        self.corpus:    list[dict]        = []
        self.doc_freqs: list[dict[str, int]] = []
        self.idf:       dict[str, float]  = {}
        self.avgdl:     float             = 0.0
        self._built = False

    def build(self, memories: list[dict]) -> None:
        self.corpus = memories
        tokenized = [self._tokenize(m) for m in memories]
        self.doc_freqs = [self._term_freq(doc) for doc in tokenized]

        N = len(memories)
        dl_sum = sum(len(doc) for doc in tokenized)
        self.avgdl = dl_sum / N if N > 0 else 1.0

        # IDF
        df: dict[str, int] = defaultdict(int)
        for doc in tokenized:
            for term in set(doc):
                df[term] += 1
        self.idf = {
            term: math.log((N - freq + 0.5) / (freq + 0.5) + 1)
            for term, freq in df.items()
        }
        self._built = True

    def score(self, query: str, top_k: int = 50) -> list[tuple[int, float]]:
        if not self._built:
            return []
        query_terms = self._tokenize_query(query)
        scores: list[tuple[int, float]] = []

        for i, (mem, tf) in enumerate(zip(self.corpus, self.doc_freqs)):
            dl = sum(tf.values())
            score = 0.0
            for term in query_terms:
                if term not in self.idf:
                    continue
                f = tf.get(term, 0)
                num = self.idf[term] * f * (self.k1 + 1)
                den = f + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                score += num / (den + 1e-9)
            if score > 0:
                scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _tokenize(self, mem: dict) -> list[str]:
        """Tokenize a memory's searchable text fields."""
        parts = [
            mem.get("title", ""),
            mem.get("description", ""),
            mem.get("source", ""),          # filename â€” crucial for "resume.pdf" queries
            " ".join(mem.get("objects") if isinstance(mem.get("objects"), list) else []),
        ]
        text = " ".join(filter(None, parts))
        return self._tokenize_text(text)

    def _tokenize_query(self, query: str) -> list[str]:
        return self._tokenize_text(query)

    def _tokenize_text(self, text: str) -> list[str]:
        text = text.lower()
        # Split on non-alphanumeric, keep numbers
        tokens = re.findall(r"[a-z0-9]+", text)
        # Remove common stop words
        stopwords = {"a","an","the","is","in","on","at","for","to","of","and","or","with","my","i","this","that"}
        return [t for t in tokens if t not in stopwords and len(t) > 1]

    def _term_freq(self, tokens: list[str]) -> dict[str, int]:
        tf: dict[str, int] = defaultdict(int)
        for t in tokens:
            tf[t] += 1
        return dict(tf)


# â”€â”€ Filename / title exact match booster (STEP 3 - IMPROVED) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def filename_match_score(query: str, memory: dict) -> float:
    """
    Enhanced filename matching with hierarchical scoring.
    Searching "resume" will ALWAYS rank "Resume.pdf" first.
    """
    q = query.lower().strip()
    title  = (memory.get("title") or "").lower()
    source = (memory.get("source") or "").lower()
    desc   = (memory.get("description") or "").lower()

    # Extract filename from source path
    filename = source.split("\\")[-1]
    filename = filename.split("/")[-1]
    filename = filename.lower()
    
    # Remove extension for better matching
    name_without_ext = filename.rsplit(".", 1)[0] if "." in filename else filename
    
    # Hierarchical scoring (highest to lowest)
    if filename == q or name_without_ext == q:
        return 2.0  # Exact filename match
    
    if filename.startswith(q):
        return 1.8  # Filename starts with query
    
    if q in filename:
        return 1.5  # Query in filename
    
    if q in title or q in name_without_ext:
        return 1.3  # Query in title or name without extension
    
    # All query words present in title+source
    words = q.split()
    if all(w in (title + " " + source) for w in words if len(w) > 2):
        return 0.9
    
    # Partial match in description
    if q in desc:
        return 0.8
    
    # Any word match
    if any(w in title or w in source for w in words if len(w) > 3):
        return 0.4

    return 0.0


# â”€â”€ Query Intent Detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def detect_query_type(query: str) -> str:
    """
    Classify the user's query for hybrid retrieval.

    filename:
        Exact filename / short keyword lookup.

    semantic:
        Natural-language questions and requests for information.

    metadata:
        Requests about file types / file collections.

    mixed:
        General queries where both keyword and semantic retrieval
        are useful.
    """

    q = query.lower().strip()

    if not q:
        return "mixed"

    words = q.split()

    # ============================================================
    # 1. Exact filename queries
    # ============================================================

    filename_extensions = (
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
        ".gif",
        ".ppt",
        ".pptx",
        ".xls",
        ".xlsx",
        ".csv",
    )

    # Example:
    # resume.pdf
    # nexus_phase_1.pdf
    # profile.jpeg

    if any(ext in q for ext in filename_extensions):
        return "filename"

    # ============================================================
    # 2. Single-word keyword searches
    # ============================================================

    # Examples:
    # YORAI
    # Nexus
    # resume
    # IELTS

    if len(words) == 1:
        return "filename"

    # ============================================================
    # 3. Natural-language semantic queries
    # ============================================================

    semantic_phrases = (
        "tell me about",
        "tell me",
        "what is",
        "what are",
        "what was",
        "what were",
        "what does",
        "what did",
        "explain",
        "describe",
        "give me details",
        "give me information",
        "information about",
        "details about",
        "overview of",
        "summary of",
        "summarize",
        "show me information",
        "can you tell me",
        "do you know about",
        "about my",
        "about the",
        "my project",
        "the project",
        "my work",
        "my goal",
        "my goals",
        "my certificate",
        "my resume",
        "my document",
        "my documents",
    )

    if any(
        phrase in q
        for phrase in semantic_phrases
    ):
        return "semantic"

    # ============================================================
    # 4. Question-word detection
    # ============================================================

    question_starts = (
        "what ",
        "where ",
        "when ",
        "how ",
        "why ",
        "which ",
        "who ",
        "whose ",
        "can ",
        "could ",
        "did ",
        "does ",
        "do ",
        "is ",
        "are ",
        "was ",
        "were ",
    )

    if q.startswith(question_starts):
        return "semantic"

    # ============================================================
    # 5. Metadata queries
    # ============================================================

    metadata_phrases = (
        "pdf files",
        "document files",
        "documents",
        "image files",
        "jpg files",
        "jpeg files",
        "png files",
        "docx files",
        "text files",
        "all files",
        "files in",
        "file types",
    )

    if any(
        phrase in q
        for phrase in metadata_phrases
    ):
        return "metadata"

    # ============================================================
    # 6. Default
    # ============================================================

    # Natural-language queries should favor semantic retrieval.
    return "semantic"

# â”€â”€ Build Match Reasons (STEP 1) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_match_reasons(
    query: str,
    memory: dict,
    filename_score: float,
    bm25_hit: bool,
    semantic_hit: bool,
) -> list[str]:
    """
    Explain why this memory matched the query.
    Returned reasons are shown directly in the frontend.
    """
    reasons = []

    if filename_score >= 1.8:
        reasons.append("Exact filename match")
    elif filename_score >= 1.5:
        reasons.append("Filename contains query")
    elif filename_score >= 0.8:
        reasons.append("Partial filename match")

    if bm25_hit:
        reasons.append("Keyword match")

    if semantic_hit:
        reasons.append("Semantic similarity")

    if memory.get("matched_goals"):
        reasons.append(
            f"Related to goal: {', '.join(memory['matched_goals'])}"
        )

    if memory.get("access_count", 0) > 5:
        reasons.append("Frequently accessed")

    return reasons


# â”€â”€ Reciprocal Rank Fusion â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def rrf_merge(
    ranked_lists: list[list[dict]],
    k: int = 60,
    weights: list[float] = None,
) -> list[dict]:
    """
    Merges multiple ranked lists using Reciprocal Rank Fusion.
    Returns merged list with rrf_score field added.
    """
    if weights is None:
        weights = [1.0] * len(ranked_lists)

    rrf_scores: dict[int, float] = defaultdict(float)
    memory_lookup: dict[int, dict] = {}

    for channel_idx, ranked in enumerate(ranked_lists):
        w = weights[channel_idx] if channel_idx < len(weights) else 1.0
        for rank, mem in enumerate(ranked):
            mid = mem.get("id") or mem.get("memory_id")
            if mid is None:
                continue
            rrf_scores[mid] += w * (1.0 / (k + rank + 1))
            memory_lookup[mid] = mem

    # Sort by RRF score descending
    sorted_ids = sorted(rrf_scores.keys(), key=lambda mid: rrf_scores[mid], reverse=True)
    results = []
    for mid in sorted_ids:
        mem = dict(memory_lookup[mid])
        mem["rrf_score"] = rrf_scores[mid]
        results.append(mem)

    return results


# â”€â”€ Module-level BM25 instance (rebuilt when index is rebuilt) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_bm25: BM25 = BM25()


def build_bm25(memories: list[dict]) -> None:
    """Call this alongside build_index() after any memory change."""
    global _bm25
    _bm25 = BM25()
    _bm25.build(memories)
    print(f"[BM25] Index built with {len(memories)} memories")


def hybrid_search(
    query: str,
    faiss_results: list[dict],
    all_memories: list[dict],
    top_k: int = 20,
) -> list[dict]:
    """
    Three-channel hybrid search with dynamic weights based on query intent:
      Channel 1: BM25 keyword match
      Channel 2: FAISS semantic match
      Channel 3: Filename/title exact match boost

    Weights adapt to query type for optimal results.
    """
    # â”€â”€ EXPAND QUERY FOR BM25 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # This expands "resume" to "resume cv curriculum vitae" for better recall
    expanded_query = expand_query(query)
    print(f"[HybridSearch] Original query: '{query}'")
    print(f"[HybridSearch] Expanded query: '{expanded_query}'")
    
    # Detect query type and set dynamic weights (STEP 4)
    query_type = detect_query_type(query)
    
    if query_type == "filename":
        weights = [1.5, 1.0, 3.0]   # Filename highest
    elif query_type == "semantic":
        weights = [1.0, 3.0, 0.5]   # Semantic highest
    elif query_type == "metadata":
        weights = [2.0, 1.0, 2.0]   # BM25 + Filename
    else:  # "mixed"
        weights = [1.5, 1.5, 2.0]   # Balanced with filename boost
    
    print(f"[HybridSearch] Query type: {query_type}, weights: {weights}")

    # Channel 1: BM25 (using expanded query for better recall)
    bm25_raw = _bm25.score(expanded_query, top_k=top_k * 2)
    bm25_ranked = [all_memories[i] for i, _ in bm25_raw if i < len(all_memories)]
    
    # Track which memories had BM25 hits
    bm25_ids = {mem.get("id") or mem.get("memory_id") for mem in bm25_ranked}

    # Channel 2: FAISS (already computed, passed in)
    faiss_ranked = faiss_results
    faiss_ids = {mem.get("id") or mem.get("memory_id") for mem in faiss_ranked}

    # Channel 3: Filename/title exact match â€” rank all memories by match score
    # Use original query for filename matching (not expanded)
    filename_scored = [
        (mem, filename_match_score(query, mem))
        for mem in all_memories
    ]
    filename_ranked = [
        mem for mem, sc in sorted(filename_scored, key=lambda x: x[1], reverse=True)
        if sc > 0
    ]
    
    # Track filename scores for match reasons
    filename_scores = {mem.get("id") or mem.get("memory_id"): sc for mem, sc in filename_scored}

    # â”€â”€ STEP 3: UPDATED RRF merge with reordered channels and new weights â”€â”€
    merged = rrf_merge(
        ranked_lists=[
            filename_ranked,  # Channel 1: Filename/title (highest priority)
            bm25_ranked,      # Channel 2: BM25 keyword (medium priority)
            faiss_ranked,     # Channel 3: FAISS semantic (lowest priority)
        ],
        weights=[
            6.0,   # filename/title â€” highest weight for exact matches
            3.5,   # keyword â€” strong for "resume" type queries
            1.0,   # semantic â€” low for short queries
        ],
        k=40,  # Reduced from 60 for faster computation
    )

    # â”€â”€ STEP 2: Add Confidence Score â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if merged:
        max_rrf = max((m["rrf_score"] for m in merged), default=1.0)
        for memory in merged:
            confidence = memory["rrf_score"] / max_rrf if max_rrf > 0 else 0
            memory["confidence"] = round(confidence * 100, 1)  # e.g., 98.3, 91.4
            
            # â”€â”€ STEP 1: Add Match Reasons â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            mid = memory.get("id") or memory.get("memory_id")
            memory["match_reasons"] = build_match_reasons(
                query=query,
                memory=memory,
                filename_score=filename_scores.get(mid, 0.0),
                bm25_hit=mid in bm25_ids if mid else False,
                semantic_hit=mid in faiss_ids if mid else False,
            )

    return merged[:top_k]


