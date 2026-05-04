"""Unit tests for SMART [M] Knowledge retrieval behavior."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import numpy as np

from namo_core.services.knowledge.knowledge_service import KnowledgeService
from namo_core.services.knowledge.tripitaka_retriever import TripitakaRetriever


def test_knowledge_search_empty_query_returns_empty_list() -> None:
    service = KnowledgeService()
    assert service.search("") == []
    assert service.search("   ") == []


def test_knowledge_search_top_k_boundary() -> None:
    service = KnowledgeService()
    mock_retriever = MagicMock()
    mock_retriever.search.return_value = [{"title": "x"}] * 10
    service._tripitaka_retriever = mock_retriever

    results = service.search("dhamma", top_k=2)
    assert len(results) == 10
    mock_retriever.search.assert_called_once_with("dhamma", top_k=2)


def test_knowledge_search_fallback_when_vector_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    retriever = TripitakaRetriever()
    retriever.is_ready = True
    retriever.has_index = True
    retriever.model = MagicMock()
    retriever.model.encode.side_effect = RuntimeError("encode failed")
    retriever.metadata = [
        {"chunk_id": "1", "title": "Nibbana", "text": "Nibbana and freedom"},
        {"chunk_id": "2", "title": "Dukkha", "text": "Suffering and its causes"},
    ]

    monkeypatch.setattr(retriever, "_keyword_search", MagicMock(return_value=[{"title": "fallback"}]))
    result = retriever.search("nibbana", top_k=1)
    assert result == [{"title": "fallback"}]
    retriever._keyword_search.assert_called_once_with("nibbana", 1)


def test_knowledge_search_diversity_filter_limits_one_source() -> None:
    retriever = TripitakaRetriever()
    retriever.is_ready = True
    retriever.has_index = False
    retriever.metadata = [
        {"chunk_id": "a", "title": "A", "text": "truth truth", "source_url": "learntripitaka.org/x"},
        {"chunk_id": "b", "title": "B", "text": "truth", "source_url": "learntripitaka.org/y"},
        {"chunk_id": "attha_c", "title": "C", "text": "truth", "source_url": "84000.co/z"},
    ]
    # Force vector path to process synthetic results
    retriever.has_index = True
    retriever.index = MagicMock()
    retriever.index.ntotal = 3
    retriever.index.search.return_value = ([[0.8, 0.7, 0.6]], [[0, 1, 2]])
    retriever.model = MagicMock()
    retriever.model.encode.return_value = np.array([[0.1, 0.2]], dtype="float32")

    results = retriever.search("truth", top_k=2, diversity=True, max_per_source=1)
    source_cats = [r["source_cat"] for r in results]
    assert len(results) == 2
    assert source_cats.count("learntripitaka") <= 1


def test_knowledge_search_thai_query_returns_list() -> None:
    service = KnowledgeService()
    results = service.search("อริยสัจ 4", top_k=3)
    assert isinstance(results, list)


def test_knowledge_search_pali_alias_nirvana_matches_nibbana_keyword_fallback() -> None:
    retriever = TripitakaRetriever()
    retriever.is_ready = True
    retriever.has_index = False
    retriever.metadata = [
        {"chunk_id": "1", "title": "Nibbana", "text": "Nibbana is liberation from suffering"},
        {"chunk_id": "2", "title": "Kamma", "text": "Kamma is intentional action"},
    ]
    results = retriever.search("nirvana nibbana", top_k=2)
    assert len(results) >= 1
    joined = " ".join((results[0].get("title", "") + " " + results[0].get("text", "")).lower().split())
    assert "nibbana" in joined
