"""Search across per-book FAISS indexes from global_library batch vectorization.

NOTE: These indexes use paraphrase-multilingual-MiniLM-L12-v2, the same model as
the Tripitaka retriever. The indexes are kept SEPARATE because they represent
different corpora (global_library vs tripitaka_main) vectorized independently —
do NOT merge the FAISS indexes as the vector populations are unrelated.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from namo_core.utils.gcs_assets import get_project_root

logger = logging.getLogger(__name__)

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_BATCH_DIR = get_project_root() / "knowledge" / "tripitaka_main" / "batch_indexes"


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
        # CPU-bound: callers must invoke via asyncio.to_thread in async contexts
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
                if "source" not in item:
                    item["source"] = "global_library"
                all_hits.append(item)
        all_hits.sort(key=lambda x: x["score"], reverse=True)
        return all_hits[:top_k]

    def add_document(self, metadata: list[dict], vectors: np.ndarray) -> None:
        """Dynamically add a new document index to the retriever and persist to disk."""
        if not metadata or len(metadata) != vectors.shape[0]:
            raise ValueError("metadata length must match vectors count")
        
        from namo_core.api.middleware import request_id_context
        trace_id = request_id_context.get()
        
        dim = vectors.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(vectors)
        
        # 1. Update In-memory state
        self.books.append({"index": index, "metadata": metadata})
        
        # 2. Persistence: Save to dynamic skills file
        try:
            timestamp = int(np.datetime64('now').astype(int))
            skill_name = f"sync_{timestamp}"
            meta_path = _BATCH_DIR / f"{skill_name}_metadata.json"
            index_path = _BATCH_DIR / f"{skill_name}.index"
            
            # Ensure directory exists
            _BATCH_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            faiss.write_index(index, str(index_path))
            logger.info(f"[{trace_id}] Skill persisted to disk: {skill_name}")
        except Exception as exc:
            logger.error(f"[{trace_id}] Failed to persist skill to disk: {exc}")


_retriever: GlobalLibraryRetriever | None = None


def get_global_library_retriever() -> GlobalLibraryRetriever:
    global _retriever
    if _retriever is None:
        _retriever = GlobalLibraryRetriever()
    return _retriever
