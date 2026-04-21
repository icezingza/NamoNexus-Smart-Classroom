from fastapi.testclient import TestClient

from namo_core.api.app import app


client = TestClient(app)


def test_knowledge_search_returns_results() -> None:
    response = client.get("/knowledge/search", params={"q": "truths"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
