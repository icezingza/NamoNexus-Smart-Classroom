"""API contract tests for POST /tts/speak and GET /tts/status."""
from fastapi.testclient import TestClient

from namo_core.api.app import app

client = TestClient(app)


def test_tts_speak_returns_expected_shape() -> None:
    response = client.post("/tts/speak", json={"text": "Hello, student."})
    assert response.status_code == 200
    payload = response.json()
    # Required keys must always be present
    assert "audio_base64" in payload
    assert "voice" in payload
    assert "chars_synthesized" in payload
    assert "provider" in payload
    assert "status" in payload


def test_tts_speak_chars_synthesized_matches_input() -> None:
    text = "The Four Noble Truths explain suffering."
    response = client.post("/tts/speak", json={"text": text})
    assert response.status_code == 200
    payload = response.json()
    assert payload["chars_synthesized"] == len(text)


def test_tts_speak_mock_returns_null_audio() -> None:
    """Mock provider should return null audio_base64 — no real bytes produced."""
    response = client.post("/tts/speak", json={"text": "Mindfulness."})
    assert response.status_code == 200
    payload = response.json()
    # Default provider is mock — audio_base64 should be None
    assert payload["audio_base64"] is None
    assert payload["provider"] == "mock"


def test_tts_speak_with_explicit_voice() -> None:
    response = client.post("/tts/speak", json={"text": "Testing.", "voice": "alloy"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["voice"] == "alloy"


def test_tts_speak_rejects_empty_text() -> None:
    response = client.post("/tts/speak", json={"text": ""})
    assert response.status_code == 422


def test_tts_speak_rejects_missing_text() -> None:
    response = client.post("/tts/speak", json={})
    assert response.status_code == 422


def test_tts_status_returns_provider_info() -> None:
    response = client.get("/tts/status")
    assert response.status_code == 200
    payload = response.json()
    assert "provider" in payload
    assert "enabled" in payload
    assert payload["enabled"] is True
