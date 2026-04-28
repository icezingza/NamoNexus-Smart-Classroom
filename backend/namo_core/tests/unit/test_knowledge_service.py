"""Unit tests for KnowledgeService and ContextBuilder."""

import pytest
from unittest.mock import MagicMock, patch

from namo_core.services.knowledge.knowledge_service import (
    ContextBuilder,
    KnowledgeService,
)


# ---------------------------------------------------------------------------
# ContextBuilder Tests
# ---------------------------------------------------------------------------


class TestContextBuilder:
    def setup_method(self):
        self.builder = ContextBuilder()

    def test_build_empty_results(self):
        assert self.builder.build([]) == ""

    def test_build_valid_results(self):
        results = [
            {
                "title": "พระสูตร A",
                "score": 0.95,
                "text": "เนื้อหาพระสูตร A",
                "source": "tripitaka",
            },
            {
                "title": "พระสูตร B",
                "score": 0.85,
                "text": "เนื้อหาพระสูตร B",
                "source": "tripitaka",
            },
        ]
        output = self.builder.build(results)

        assert "ข้อมูลเกี่ยวข้อง:" in output
        assert "[1] พระสูตร A (score=0.95, source=tripitaka)" in output
        assert "เนื้อหาพระสูตร A" in output
        assert "[2] พระสูตร B (score=0.85, source=tripitaka)" in output
        assert "เนื้อหาพระสูตร B" in output

    def test_build_truncates_long_text(self):
        long_text = "A" * 600
        results = [
            {"title": "Long Text", "score": 1.0, "text": long_text, "source": "test"}
        ]
        output = self.builder.build(results)

        # Should contain exactly 500 'A's, not 600
        assert "A" * 500 in output
        assert "A" * 501 not in output

    def test_build_handles_missing_keys_gracefully(self):
        results = [{"title": "Only Title"}]  # Missing score, text, and source
        output = self.builder.build(results)

        assert "[1] Only Title (score=0.00, source=unknown)" in output


# ---------------------------------------------------------------------------
# KnowledgeService Tests
# ---------------------------------------------------------------------------


class TestKnowledgeService:
    def test_search_empty_query(self):
        service = KnowledgeService()
        assert service.search("") == []
        assert service.search("   ") == []

    @patch(
        "namo_core.services.knowledge.knowledge_service.KnowledgeService._get_tripitaka_retriever"
    )
    def test_search_valid_query(self, mock_get_retriever):
        mock_retriever = MagicMock()
        mock_retriever.search.return_value = [{"title": "Result", "score": 0.9}]
        mock_get_retriever.return_value = mock_retriever

        service = KnowledgeService()
        results = service.search("อริยสัจ 4", top_k=2)

        mock_retriever.search.assert_called_once_with("อริยสัจ 4", top_k=2)
        assert len(results) == 1
        assert results[0]["title"] == "Result"

    @patch(
        "namo_core.services.knowledge.knowledge_service.KnowledgeService._get_tripitaka_retriever"
    )
    @patch("namo_core.services.knowledge.knowledge_service.logger")
    def test_search_exception_handled(self, mock_logger, mock_get_retriever):
        mock_retriever = MagicMock()
        mock_retriever.search.side_effect = Exception("FAISS crashed")
        mock_get_retriever.return_value = mock_retriever

        service = KnowledgeService()
        results = service.search("test")

        assert results == []
        mock_logger.warning.assert_called_once()
        assert "Tripitaka search failed" in mock_logger.warning.call_args[0][0]
