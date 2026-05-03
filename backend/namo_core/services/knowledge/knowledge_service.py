"""KnowledgeService — RAG search + context building with semantic caching."""

import logging
from typing import Dict, Any, Optional

from namo_core.services.knowledge.global_library_retriever import GlobalLibraryRetriever, get_global_library_retriever

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

    def build_with_slide(
        self,
        items: list[Dict[str, Any]],
        slide: Optional[Dict[str, Any]] = None,
        teaching_hint: str = "",
    ) -> str:
        parts: list[str] = []
        if teaching_hint:
            parts.append(f"คำแนะนำการสอน: {teaching_hint}")
        if slide:
            parts.append(
                "สไลด์ปัจจุบัน: "
                f"{slide.get('slide_number', '')} {slide.get('title', '')} "
                f"{slide.get('dhamma_point', '')}"
            )
        if items:
            normalized = []
            for item in items:
                normalized.append(
                    {
                        "title": item.get("title", "Unknown"),
                        "score": item.get("score", 0.0),
                        "text": item.get("text") or item.get("content", ""),
                        "source": item.get("source", "unknown"),
                    }
                )
            parts.append(self.build(normalized))
        return "\n\n".join(p for p in parts if p)


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

    @property
    def global_lib(self) -> GlobalLibraryRetriever:
        return get_global_library_retriever()

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

        results: list[Dict[str, Any]] = []

        try:
            retriever = self._get_tripitaka_retriever()
            if retriever:
                tripitaka_hits = retriever.search(query, top_k=top_k)
                if tripitaka_hits:
                    results.extend(tripitaka_hits)
        except Exception as exc:
            logger.warning(f"Tripitaka search failed: {exc}")

        try:
            gl_hits = self.global_lib.search(query, top_k=3)
            for hit in gl_hits:
                hit["source"] = "global_library"
            results.extend(gl_hits)
        except Exception as exc:
            logger.warning("GlobalLibrary search failed: %s", exc)

        return results

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
