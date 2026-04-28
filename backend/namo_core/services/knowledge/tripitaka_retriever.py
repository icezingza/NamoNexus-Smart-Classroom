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
# parents[4]: backend/namo_core/services/knowledge/tripitaka_retriever.py
#             [0]=knowledge  [1]=services  [2]=namo_core  [3]=backend  [4]=project root
_BASE_DIR      = Path(__file__).resolve().parents[4]  # → C:\Users\icezi\NamoNexus-Smart-Classroom
_KNOWLEDGE_DIR = _BASE_DIR / "knowledge"
_TRIPITAKA_DIR = _KNOWLEDGE_DIR / "tripitaka_main"
# ใช้ไฟล์ 162,895 vectors (248 MB) — copy มาจาก namo_core_project
_INDEX_FILE    = _TRIPITAKA_DIR / "tripitaka_index.faiss"
_META_FILE     = _TRIPITAKA_DIR / "tripitaka_metadata.json"
_MOCK_FILE     = _KNOWLEDGE_DIR / "mock_tripitaka.json"
_MODEL_NAME    = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Golden Ratio for Bayesian score weighting (Phase 11.1 invariant)
_PHI = 1.6180339887

# ---------------------------------------------------------------------------
# Singleton holder
# ---------------------------------------------------------------------------
_retriever_instance: "TripitakaRetriever | None" = None


def _classify_source(chunk_id: str, source_url: str) -> str:
    """Classify a chunk into a source category for diversity bucketing."""
    if not source_url:
        return "other"
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
        is_ready  : True if at least metadata is loaded
        has_index : True if FAISS vector index is loaded
    """

    def __init__(self) -> None:
        self.model: SentenceTransformer | None = None
        self.index: Any | None = None
        self.metadata: list[dict] = []
        self.is_ready: bool = False
        self.has_index: bool = False
        self._load()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load FAISS index + metadata + embedding model into memory."""
        # Check for main metadata or mock file
        meta_to_load = None
        if _META_FILE.exists():
            meta_to_load = _META_FILE
        elif _MOCK_FILE.exists():
            meta_to_load = _MOCK_FILE
            logger.info("Using mock tripitaka data from %s", _MOCK_FILE)

        if not meta_to_load:
            logger.warning("No tripitaka metadata or mock file found.")
            return

        try:
            with open(meta_to_load, encoding="utf-8") as f:
                self.metadata = json.load(f)
            self.is_ready = True

            # Try to load FAISS index if available
            if _INDEX_FILE.exists():
                logger.info("Loading Tripitaka FAISS index from %s", _INDEX_FILE)
                self.index = faiss.read_index(str(_INDEX_FILE))
                self.has_index = True
                
                logger.info("Loading embedding model: %s", _MODEL_NAME)
                self.model = SentenceTransformer(_MODEL_NAME)
            else:
                logger.info("FAISS index missing. Using keyword search fallback.")

            logger.info("TripitakaRetriever ready (metadata loaded)")

        except Exception as exc:
            logger.error("Failed to initialize TripitakaRetriever: %s", exc)
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
        if not self.is_ready or not query.strip():
            return []

        # -- Case A: Vector Search (High Accuracy) --
        if self.has_index and self.model:
            try:
                q_vec = self.model.encode(
                    [query.strip()],
                    show_progress_bar=False,
                    convert_to_numpy=True,
                ).astype(np.float32)
                faiss.normalize_L2(q_vec)

                pool_size = (top_k * max_per_source * 6) if diversity else top_k
                k = min(max(pool_size, top_k * 5), self.index.ntotal)
                scores, indices = self.index.search(q_vec, k)

                return self._process_results(scores[0], indices[0], top_k, diversity, max_per_source)
            except Exception as exc:
                logger.error("Vector search failed, falling back to keyword: %s", exc)

        # -- Case B: Keyword Search Fallback (Robustness) --
        return self._keyword_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int) -> list[dict]:
        """Simple keyword matching fallback."""
        query_words = query.lower().split()
        results = []
        for entry in self.metadata:
            text = entry.get("text", "").lower()
            title = entry.get("title", "").lower()
            
            # Simple scoring: how many query words match?
            score = sum(1 for word in query_words if word in text or word in title)
            if score > 0:
                results.append({
                    "chunk_id": entry.get("chunk_id", "mock"),
                    "title": entry.get("title", "Unknown"),
                    "source_url": entry.get("source_url", ""),
                    "text": entry.get("text", ""),
                    "score": float(score),
                    "source_cat": "fallback"
                })
        
        # Sort by score and take top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _process_results(self, scores, indices, top_k, diversity, max_per_source) -> list[dict]:
        source_counts: dict[str, int] = defaultdict(int)
        results: list[dict] = []
        leftover: list[dict] = []

        for score, idx in zip(scores, indices):
            if idx < 0 or idx >= len(self.metadata):
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
                if len(leftover) < top_k:
                    leftover.append(item)
                continue

            source_counts[cat] += 1
            results.append(item)
            if len(results) >= top_k:
                break

        if len(results) < top_k:
            seen_ids = {r["chunk_id"] for r in results}
            for item in leftover:
                if len(results) >= top_k: break
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


def search_tripitaka(query: str, top_k: int = 3) -> list[dict]:
    """Search the Tripitaka index via the singleton instance."""
    return get_tripitaka_retriever().search(query, top_k=top_k)


# -------------------------