"""
semantic_cache.py - In-memory cache for frequently asked Dhamma questions with semantic similarity
Integrates with database for persistent cache storage (Phase 12).
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple, Callable
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Optional database persistence callback (set by dependency injection)
_db_save_callback: Optional[Callable] = None


class SemanticCache:
    """
    A lightweight caching layer with semantic similarity matching.
    Uses sentence embeddings to find similar queries even if worded differently.
    Reduces latency from ~4s to <100ms for repeated/similar questions.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.cache = []
            cls._instance.embeddings = []
            cls._instance.max_size = 50
            cls._instance.similarity_threshold = 0.85
            cls._instance.ttl_seconds = 86400  # 24 hours default
            try:
                cls._instance.model = SentenceTransformer('all-MiniLM-L6-v2')
                cls._instance.model_loaded = True
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}. Falling back to exact matching.")
                cls._instance.model = None
                cls._instance.model_loaded = False
        return cls._instance

    def _encode_query(self, query: str) -> Optional[np.ndarray]:
        """Generate embedding for a query."""
        if not self.model_loaded or self.model is None:
            return None
        try:
            embedding = self.model.encode(query.strip(), convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.warning(f"Error encoding query: {e}")
            return None

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        magnitude = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        return dot_product / magnitude if magnitude > 0 else 0.0

    def get_cached_response(self, query: str) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Retrieve cached response if semantically similar to a past query.
        Returns tuple of (response, similarity_score).
        Skips expired entries (TTL-based) and updates last_accessed timestamp.
        """
        query_embedding = self._encode_query(query)
        best_match = None
        best_similarity = 0.0
        current_time = time.time()

        for i, item in enumerate(self.cache):
            # Skip expired entries
            if current_time - item["timestamp"] > self.ttl_seconds:
                continue

            if query_embedding is not None and self.embeddings[i] is not None:
                similarity = self._cosine_similarity(query_embedding, self.embeddings[i])
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = item

        if best_match and best_similarity >= self.similarity_threshold:
            # Update last_accessed for LRU tracking
            best_match["last_accessed"] = current_time
            logger.info(
                f"[Semantic Cache] HIT! (similarity: {best_similarity:.2f}) "
                f"Query: '{query.strip()}' matched '{best_match['question']}'"
            )
            return best_match["response"], best_similarity

        return None, 0.0

    def add_to_cache(self, query: str, response: Dict[str, Any]):
        """Save a new question-answer pair with its embedding (LRU eviction)."""
        query_normalized = query.strip().lower()

        # Ignore if already exists
        if any(item["question"] == query_normalized for item in self.cache):
            return

        embedding = self._encode_query(query_normalized)
        current_time = time.time()

        # LRU eviction: remove least recently used entry when cache is full
        if len(self.cache) >= self.max_size:
            # Find index of entry with minimum last_accessed timestamp
            min_idx = min(
                range(len(self.cache)),
                key=lambda i: self.cache[i].get("last_accessed", self.cache[i]["timestamp"])
            )
            self.cache.pop(min_idx)
            self.embeddings.pop(min_idx)
            logger.debug("[Semantic Cache] LRU eviction: removed least recently used entry")

        self.cache.append(
            {
                "question": query_normalized,
                "response": response,
                "timestamp": current_time,
                "last_accessed": current_time,
            }
        )
        self.embeddings.append(embedding)

        # Persist to database if callback is available
        if _db_save_callback:
            try:
                _db_save_callback(query_normalized, response, embedding)
            except Exception as e:
                logger.warning(f"Failed to persist cache to DB: {e}")

    def set_similarity_threshold(self, threshold: float):
        """Adjust similarity threshold (0.0 to 1.0). Higher = more strict matching."""
        if 0.0 <= threshold <= 1.0:
            self.similarity_threshold = threshold
            logger.info(f"[Semantic Cache] Similarity threshold set to {threshold}")
        else:
            logger.warning(f"Invalid threshold {threshold}. Must be between 0.0 and 1.0")

    def set_ttl(self, seconds: int):
        """Set Time-To-Live for cache entries in seconds."""
        if seconds > 0:
            self.ttl_seconds = seconds
            logger.info(f"[Semantic Cache] TTL set to {seconds} seconds ({seconds // 3600}h)")
        else:
            logger.warning(f"Invalid TTL {seconds}. Must be > 0")


def set_db_save_callback(callback: Callable):
    """Register database persistence callback (called when cache entries are added)."""
    global _db_save_callback
    _db_save_callback = callback
    logger.debug("Database persistence callback registered for semantic cache")


# Global Singleton Instance
query_cache = SemanticCache()
