from fastapi.testclient import TestClient

from namo_core.api.app import app


client = TestClient(app)


def test_reasoning_endpoint_returns_answer_and_sources() -> None:
    response = client.post("/reasoning/explain", json={"query": "Four Noble Truths"})
    assert response.status_code == 200
    payload = response.json()
    assert "answer" in payload
    assert "context" in payload
    assert isinstance(payload["sources"], list)
    assert payload["provider"] == "mock"


def test_reasoning_chat_endpoint_returns_answer_and_sources() -> None:
    response = client.post(
        "/reasoning/chat",
        json={
            "messages": [
                {"role": "system", "content": "Keep answers brief."},
                {"role": "user", "content": "Explain mindfulness."},
            ]
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "Explain mindfulness."
    assert "answer" in payload
    assert "context" in payload
    assert isinstance(payload["sources"], list)
    assert payload["provider"] == "mock"
