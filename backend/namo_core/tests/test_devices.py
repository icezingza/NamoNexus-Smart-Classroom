from fastapi.testclient import TestClient

from namo_core.api.app import app


client = TestClient(app)


def test_devices_endpoint_returns_projector_and_microphone() -> None:
    response = client.get("/devices")
    assert response.status_code == 200
    payload = response.json()
    assert payload["projector"]["status"] == "standby"
    assert payload["microphone"]["status"] == "ready"
