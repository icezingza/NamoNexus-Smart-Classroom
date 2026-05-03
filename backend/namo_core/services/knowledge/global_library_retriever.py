"""Search across per-book FAISS indexes from global_library batch vectorization.

NOTE: These indexes use paraphrase-multilingual-MiniLM-L12-v2 (L12 embedding space).
Do NOT merge with tripitaka_index.faiss (all-MiniLM-L6-v2 / L6 space).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_BATCH_DIR = Path(__file__).resolve().parents[4] / "knowledge" / "tripitaka_main" / "batch_indexes"


class GlobalLibraryRetriever:
    def __init__(self) -> None:
        logger.info("GlobalLibraryRetriever: loading model %s", _MODEL_NAME)
        self.model = SentenceTransformer(_MODEL_NAME)
        self.books: list[dict] = []
        self._load_indexes()

    def _load_indexes(self) -> None:
        if not _BATCH_DIR.exists():
            logger.warning("batch_indexes dir not found: %s", _BATCH_DIR)
            return
        for meta_path in sorted(_BATCH_DIR.glob("*_metadata.json")):
            index_path = _BATCH_DIR / meta_path.name.replace("_metadata.json", ".index")
            if not index_path.exists():
                logger.warning("Missing index for %s -- skipped", meta_path.name)
                continue
            try:
                index = faiss.read_index(str(index_path))
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                self.books.append({"index": index, "metadata": metadata})
            except Exception as exc:
                logger.error("Failed to load %s: %s", index_path.name, exc)
        logger.info("GlobalLibraryRetriever: loaded %d book indexes", len(self.books))

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not self.books:
            return []
        vec = self.model.encode([query], normalize_embeddings=True).astype("float32")
        all_hits: list[dict] = []
        for book in self.books:
            n = min(top_k, book["index"].ntotal)
            if n == 0:
                continue
            scores, indices = book["index"].search(vec, n)
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= len(book["metadata"]):
                    if idx >= 0:
                        logger.warning("FAISS returned out-of-range idx %d (metadata len %d)", idx, len(book["metadata"]))
                    continue
                item = dict(book["metadata"][idx])
                item["score"] = float(score)
                all_hits.append(item)
        all_hits.sort(key=lambda x: x["score"], reverse=True)
        return all_hits[:top_k]


_retriever: GlobalLibraryRetriever | None = None


def get_global_library_retriever() -> GlobalLibraryRetriever:
    global _retriever
    if _retriever is None:
        _retriever = GlobalLibraryRetriever()
    return _retriever
