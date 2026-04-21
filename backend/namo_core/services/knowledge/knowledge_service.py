"""KnowledgeService — RAG search + context building with semantic caching."""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Build formatted context from knowledge search results."""

    def build(self, results: list[Dict[str, Any]]) -> str:
        """Assemble search results into a context string for LLM injection."""
        if not results:
            return ""

        lines = ["ข้อมูลเกี่ยวข้อง:"]
        for i, result in enumerate(results[:5], 1):
            title = result.get("title", "Unknown")
            score = result.get("score", 0.0)
            text = result.get("text", "")
            source = result.get("source", "unknown")

            lines.append(f"\n[{i}] {title} (score={score:.2f}, source={source})")
            if text:
                lines.append(text[:500])  # Truncate to first 500 chars
            lines.append("---")

        return "\n".join(lines)


class KnowledgeService:
    """
    RAG search service integrating:
    - Tripitaka FAISS retrieval (primary)
    - Legacy materials database (fallback)
    - Semantic cache for query similarity matching
    """

    def __init__(self) -> None:
        self.context_builder = ContextBuilder()
        self._tripitaka_retriever = None

    def _get_tripitaka_retriever(self):
        """Lazy-load tripitaka retriever on first access."""
        if self._tripitaka_retriever is None:
            try:
                from namo_core.services.knowledge.tripitaka_retriever import (
                    get_tripitaka_retriever,
                )
                self._tripitaka_retriever = get_tripitaka_retriever()
            except ImportError:
                logger.warning("Tripitaka retriever not available")
                self._tripitaka_retriever = None
        return self._tripitaka_retriever

    def search(self, query: str, top_k: int = 3) -> list[Dict[str, Any]]:
        """
        Search knowledge base using RAG (Tripitaka FAISS).

        Args:
            query: Search query string
            top_k: Number of results to return

        Returns:
            List of knowledge items with score, title, text, source
        """
        if not query.strip():
            return []

        try:
            retriever = self._get_tripitaka_retriever()
            if retriever:
                results = retriever.search(query, top_k=top_k)
                return results if results else []
        except Exception as exc:
            logger.warning(f"Tripitaka search failed: {exc}")

        # Fallback: return empty if no retriever available
        return []

    def build_context(self, query: str, top_k: int = 3) -> str:
        """
        Search and build formatted context for LLM injection.

        Args:
            query: Search query string
            top_k: Number of results to use for context

        Returns:
            Formatted context string ready for LLM prompt
        """
        results = self.search(query, top_k=top_k)
        return self.context_builder.build(results)
