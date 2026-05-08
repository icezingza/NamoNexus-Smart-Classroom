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

    def test_build_with_mixed_sources(self):
        results = [
            {"title": "Sutta A", "score": 0.9, "text": "Text A", "source": "tripitaka"},
            {
                "title": "Commentary B",
                "score": 0.7,
                "text": "Text B",
                "source": "atthakatha",
            },
        ]
        output = self.builder.build(results)
        assert "source=tripitaka" in output
        assert "source=atthakatha" in output

    def test_build_extreme_truncation(self):
        """Ensure truncation works even with very small limits if configured."""
        # Assuming the builder might eventually take a max_length param,
        # but for now testing the hardcoded 500 limit.
        results = [
            {"title": "Short", "score": 1.0, "text": "A" * 1000, "source": "test"}
        ]
        output = self.builder.build(results)

        # Find the start of the text block and check its length
        text_part = output.split("] Short")[1].split("--------------------")[0].strip()
        # Based on current implementation, it looks for the first 500 chars
        assert len(text_part) <= 550  # Account for headers/score info
        assert "A" * 501 not in output

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
        """Tripitaka returns 1 hit; GlobalLibrary property mocked via patch.object."""
        mock_retriever = MagicMock()
        mock_retriever.search.return_value = [{"title": "Result", "score": 0.9}]
        mock_get_retriever.return_value = mock_retriever

        # Mock global_lib property so it returns empty — isolates tripitaka results
        mock_gl = MagicMock()
        mock_gl.search.return_value = []

        with patch(
            "namo_core.services.knowledge.knowledge_service.get_global_library_retriever",
            return_value=mock_gl,
        ):
            service = KnowledgeService()
            results = service.search("อริยสัจ 4", top_k=2)

        mock_retriever.search.assert_called_once_with("อริยสัจ 4", top_k=2)
        assert any(r["title"] == "Result" for r in results)

    @patch(
        "namo_core.services.knowledge.knowledge_service.KnowledgeService._get_tripitaka_retriever"
    )
    def test_search_respects_top_k_parameter(self, mock_get_retriever):
        mock_retriever = MagicMock()
        mock_retriever.search.return_value = []
        mock_get_retriever.return_value = mock_retriever

        with patch(
            "namo_core.services.knowledge.knowledge_service.get_global_library_retriever",
            return_value=MagicMock(search=MagicMock(return_value=[])),
        ):
            service = KnowledgeService()
            service.search("test", top_k=10)

        mock_retriever.search.assert_called_once_with("test", top_k=10)


    @patch(
        "namo_core.services.knowledge.knowledge_service.KnowledgeService._get_tripitaka_retriever"
    )
    @patch("namo_core.services.knowledge.knowledge_service.logger")
    def test_search_exception_handled(self, mock_logger, mock_get_retriever):
        """Both sources fail → returns [] and logs warnings."""
        mock_retriever = MagicMock()
        mock_retriever.search.side_effect = Exception("FAISS crashed")
        mock_get_retriever.return_value = mock_retriever

        mock_gl = MagicMock()
        mock_gl.search.side_effect = Exception("GL down")

        with patch(
            "namo_core.services.knowledge.knowledge_service.get_global_library_retriever",
            return_value=mock_gl,
        ):
            service = KnowledgeService()
            results = service.search("test")

        assert results == []
        assert mock_logger.warning.call_count >= 1
        warning_messages = [str(call) for call in mock_logger.warning.call_args_list]
        assert any("Tripitaka search failed" in msg for msg in warning_messages)
