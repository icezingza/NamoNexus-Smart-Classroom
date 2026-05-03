import pytest
from unittest.mock import patch, MagicMock
import numpy as np


def test_retriever_returns_results_for_valid_query():
    from namo_core.services.knowledge.global_library_retriever import GlobalLibraryRetriever
    retriever = GlobalLibraryRetriever.__new__(GlobalLibraryRetriever)
    retriever.books = [
        {
            "index": MagicMock(**{"ntotal": 2, "search.return_value": (
                np.array([[0.9, 0.8]]),
                np.array([[0, 1]])
            )}),
            "metadata": [
                {"content": "ธรรมะคือความจริง", "title": "บทที่ 1", "book": "test"},
                {"content": "ศีลทำให้จิตสงบ", "title": "บทที่ 2", "book": "test"},
            ],
        }
    ]
    retriever.model = MagicMock(
        encode=MagicMock(return_value=np.array([[0.1] * 384]))
    )

    results = retriever.search("ธรรมะ", top_k=2)

    assert len(results) == 2
    assert results[0]["content"] == "ธรรมะคือความจริง"
    assert results[0]["score"] >= results[1]["score"]


def test_retriever_returns_empty_for_no_books():
    from namo_core.services.knowledge.global_library_retriever import GlobalLibraryRetriever
    retriever = GlobalLibraryRetriever.__new__(GlobalLibraryRetriever)
    retriever.books = []
    retriever.model = MagicMock(encode=MagicMock(return_value=np.array([[0.1] * 384])))

    results = retriever.search("test", top_k=5)
    assert results == []


def test_retriever_skips_out_of_range_faiss_index():
    from namo_core.services.knowledge.global_library_retriever import GlobalLibraryRetriever
    retriever = GlobalLibraryRetriever.__new__(GlobalLibraryRetriever)
    retriever.books = [
        {
            "index": MagicMock(**{"ntotal": 1, "search.return_value": (
                np.array([[0.9, 0.5]]),
                np.array([[0, 99]])  # idx=99 is out of range for 1-item metadata
            )}),
            "metadata": [
                {"content": "valid chunk", "title": "test", "book": "test"},
            ],
        }
    ]
    retriever.model = MagicMock(
        encode=MagicMock(return_value=np.array([[0.1] * 384]))
    )

    results = retriever.search("query", top_k=2)

    assert len(results) == 1  # only the in-range result
    assert results[0]["content"] == "valid chunk"
