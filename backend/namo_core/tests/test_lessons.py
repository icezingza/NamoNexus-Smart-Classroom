from fastapi.testclient import TestClient

from namo_core.api.app import app


client = TestClient(app)


def test_lesson_outline_endpoint_returns_steps() -> None:
    response = client.get("/lessons/outline")
    assert response.status_code == 200
    payload = response.json()
    assert payload["lesson_id"]
    assert len(payload["steps"]) == 3
