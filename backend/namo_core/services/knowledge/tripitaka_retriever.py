"""
tripitaka_retriever.py - Phase 11 RAG Retriever Service
=========================================================
Loads FAISS Index + Metadata produced by master_ingestion.py
Exposes search_tripitaka() for API routes and ClassroomPipeline.

Design:
  - Singleton Pattern: loads model + index once at server start
    via get_tripitaka_retriever() -- saves RAM, faster response
  - Cosine Similarity via IndexFlatIP + normalize_L2
  - Source Diversity Filter (Phase 11D): limits results per source
    category so RAG context is not dominated by one source.
  - Graceful fallback: if index file missing (pre-ingestion)
    returns [] without crashing server

Author: Senior AI Engineer (NRE Phase 11.4 / 11D)
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_TRIPITAKA_DIR = Path(__file__).parent.parent.parent / "knowledge" / "tripitaka"
_INDEX_FILE    = _TRIPITAKA_DIR / "tripitaka_index.faiss"
_META_FILE     = _TRIPITAKA_DIR / "tripitaka_metadata.json"
_MODEL_NAME    = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Golden Ratio for Bayesian score weighting (Phase 11.1 invariant)
_PHI = 1.6180339887

# Source categories for diversity bucketing
_SOURCE_CATEGORIES = {
    "learntripitaka": "learntripitaka",
    "84000_attha":    "84000_attha",
    "84000_other":    "84000_other",
    "dhamma_talk":    "dhamma_talk",
    "jataka":         "jataka",
    "other":          "other",
}

# ---------------------------------------------------------------------------
# Singleton holder
# ---------------------------------------------------------------------------
_retriever_instance: "TripitakaRetriever | None" = None


def _classify_source(chunk_id: str, source_url: str) -> str:
    """Classify a chunk into a source category for diversity bucketing."""
    if "learntripitaka" in source_url:
        return "learntripitaka"
    if chunk_id.startswith("attha_"):
        return "84000_attha"
    if "dhamma_talk" in chunk_id or "dhammatalks" in source_url:
        return "dhamma_talk"
    if "jataka" in chunk_id or "jataka" in source_url:
        return "jataka"
    if "84000" in source_url or "84000" in chunk_id:
        return "84000_other"
    return "other"


class TripitakaRetriever:
    """
    RAG Retriever for Tripitaka knowledge base (Phase 11).

    Attributes:
        model     : SentenceTransformer for query embedding
        index     : faiss.IndexFlatIP (cosine similarity)
        metadata  : list[dict] mapping faiss_id -> chunk data
        is_ready  : False if index file missing (pre-ingestion)
    """

    def __init__(self) -> None:
        self.model: SentenceTransformer | None = None
        self.index: Any | None = None
        self.metadata: list[dict] = []
        self.is_ready: bool = False
        self._load()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load FAISS index + metadata + embedding model into memory."""
        if not _INDEX_FILE.exists() or not _META_FILE.exists():
            logger.warning(
                "Tripitaka FAISS index not found at %s - "
                "run master_ingestion.py first. "
                "Retriever will return empty results until index is available.",
                _TRIPITAKA_DIR,
            )
            return

        try:
            logger.info("Loading Tripitaka FAISS index from %s", _INDEX_FILE)
            self.index = faiss.read_index(str(_INDEX_FILE))

            with open(_META_FILE, encoding="utf-8") as f:
                self.metadata = json.load(f)

            logger.info("Loading embedding model: %s", _MODEL_NAME)
            self.model = SentenceTransformer(_MODEL_NAME)

            self.is_ready = True
            logger.info(
                "TripitakaRetriever ready - %d vectors, dim=%d",
                self.index.ntotal,
                self.index.d,
            )

        except Exception as exc:
            logger.error(
                "Failed to initialize TripitakaRetriever: %s", exc, exc_info=True
            )
            self.is_ready = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 5,
        diversity: bool = True,
        max_per_source: int = 2,
    ) -> list[dict]:
        """
        Search for relevant chunks using Cosine Similarity + Source Diversity Filter.

        Args:
            query          : search query (Thai or English)
            top_k          : number of results to return (default 5)
            diversity      : enable source diversity filter (default True)
                             When True, at most `max_per_source` results
                             come from the same source category, so results
                             draw from learntripitaka, 84000_attha, etc.
            max_per_source : max results per source category (default 2)

        Returns:
            list[dict] sorted by score, each item:
                chunk_id   : str
                title      : str
                source_url : str
                text       : str
                score      : float  (cosine * PHI Bayesian weight)
                source_cat : str    (diversity bucket label)
        """
        if not self.is_ready:
            logger.warning("TripitakaRetriever.search() called but index not ready")
            return []

        if not query.strip():
            return []

        # Embed + normalize query vector
        q_vec = self.model.encode(
            [query.strip()],
            show_progress_bar=False,
            convert_to_numpy=True,
        ).astype(np.float32)
        faiss.normalize_L2(q_vec)

        # Search a larger pool so diversity filter has candidates to pick from
        pool_size = (top_k * max_per_source * len(_SOURCE_CATEGORIES)) if diversity else top_k
        pool_size = max(pool_size, top_k * 5)
        k = min(pool_size, self.index.ntotal)
        scores, indices = self.index.search(q_vec, k)

        # ── Diversity-aware selection ──────────────────────────────────────
        source_counts: dict[str, int] = defaultdict(int)
        results: list[dict] = []
        leftover: list[dict] = []   # candidates blocked by diversity cap

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue

            entry = self.metadata[idx]
            cid   = entry.get("chunk_id", "")
            url   = entry.get("source_url", "")
            cat   = _classify_source(cid, url)
            bscore = round(float(score) * _PHI, 4)

            item = {
                "chunk_id":   cid,
                "title":      entry.get("title", ""),
                "source_url": url,
                "text":       entry.get("text", ""),
                "score":      bscore,
                "source_cat": cat,
            }

            if diversity and source_counts[cat] >= max_per_source:
                # Save for fallback if we run short
                if len(leftover) < top_k:
                    leftover.append(item)
                continue

            source_counts[cat] += 1
            results.append(item)

            if len(results) >= top_k:
                break

        # Fill remaining slots from leftover (best scores first)
        if len(results) < top_k:
            seen_ids = {r["chunk_id"] for r in results}
            for item in leftover:
                if len(results) >= top_k:
                    break
                if item["chunk_id"] not in seen_ids:
                    results.append(item)
                    seen_ids.add(item["chunk_id"])

        return results

    def describe(self) -> dict:
        """Return index summary for /status endpoint."""
        if not self.is_ready:
            return {"status": "not_ready", "vectors": 0, "model": _MODEL_NAME}
        return {
            "status":     "ready",
            "vectors":    self.index.ntotal,
            "dim":        self.index.d,
            "model":      _MODEL_NAME,
            "index_file": str(_INDEX_FILE),
        }


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

def get_tripitaka_retriever() -> TripitakaRetriever:
    """Return (or create) the TripitakaRetriever singleton."""
    global _retriever_instance
    if _retriever_instance is None:
        logger.info("Initializing TripitakaRetriever singleton...")
        _retriever_instance = TripitakaRetriever()
    return _retriever_instance


# ---------------------------------------------------------------------------
# Module-level convenience (used by ClassroomPipeline)
# ---------------------------------------------------------------------------

def search_tripitaka(
    query: str,
    top_k: int = 5,
    diversity: bool = True,
    max_per_source: int = 2,
) -> list[dict]:
    """
    Convenience wrapper -- callers don't need to manage the singleton.

    Usage::

        from namo_core.services.knowledge.tripitaka_retriever import search_tripitaka
        results = search_tripitaka("ศีล 5 คืออะไร", top_k=5)
    """
    return get_tripitaka_retriever().search(
        query, top_k=top_k, diversity=diversity, max_per_source=max_per_source
    )
