from fastapi.testclient import TestClient

from namo_core.api.app import app


client = TestClient(app)


def test_status_endpoint_exposes_pipeline_summary() -> None:
    response = client.get("/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["backend"] == "online"
    assert payload["knowledge_index"]["indexed_items"] >= 1
    assert payload["pipeline"]["intent"] == "guide-lesson"
