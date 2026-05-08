"""Foundation smoke test — GET /status basic contract."""
from fastapi.testclient import TestClient

from namo_core.api.app import app

client = TestClient(app)


def test_status_endpoint_exposes_pipeline_summary() -> None:
    response = client.get("/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["project"] == "Namo Core"
    assert payload["backend"] == "online"
    # knowledge_index key exists and has indexed_items
    index = payload.get("knowledge_index", {})
    assert isinstance(index, dict)
    assert index.get("indexed_items", 0) >= 0
    # orchestrator_ready flag is present
    assert "orchestrator_ready" in payload
