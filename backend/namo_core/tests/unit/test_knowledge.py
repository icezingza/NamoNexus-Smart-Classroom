from fastapi.testclient import TestClient

from namo_core.api.app import app
from namo_core.services.knowledge.knowledge_service import KnowledgeService

client = TestClient(app)


def test_knowledge_search_returns_results() -> None:
    response = client.get("/knowledge/search", params={"q": "truths"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1


def test_knowledge_corpus_expanded_to_at_least_20_items() -> None:
    service = KnowledgeService()
    assert service.catalog_size >= 20, (
        f"Expected ≥20 items after corpus expansion, got {service.catalog_size}"
    )


def test_knowledge_index_uses_tfidf_plus_backend() -> None:
    service = KnowledgeService()
    summary = service.index_summary()
    assert summary["backend"] == "tf-idf-plus"


def test_knowledge_search_pali_alias_nirvana_finds_nibbana_content() -> None:
    service = KnowledgeService()
    results = service.search("nirvana")
    assert len(results) > 0, "Pali alias 'nirvana' should match 'nibbana' content"
    titles = [r["title"] for r in results]
    # The Nibbana Sutta or concepts doc should be in results
    assert any("nibb" in t.lower() or "nirvana" in t.lower() or "Nibbana" in t for t in titles)


def test_knowledge_search_four_noble_truths_phrase() -> None:
    service = KnowledgeService()
    results = service.search("four noble truths")
    assert len(results) > 0
    assert results[0]["score"] > 0


def test_knowledge_search_karma_finds_results() -> None:
    service = KnowledgeService()
    results = service.search("karma rebirth")
    assert len(results) > 0
