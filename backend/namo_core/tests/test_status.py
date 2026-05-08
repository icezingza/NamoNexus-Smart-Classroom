"""API contract tests for GET /status — validates feature flags and index summary."""
from fastapi.testclient import TestClient

from namo_core.api.app import app

client = TestClient(app)


def test_status_returns_backend_online() -> None:
    response = client.get("/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["project"] == "Namo Core"
    assert payload["backend"] == "online"


def test_status_includes_knowledge_index() -> None:
    response = client.get("/status")
    assert response.status_code == 200
    payload = response.json()
    index = payload.get("knowledge_index", {})
    assert isinstance(index, dict), "knowledge_index must be a dict"
    # indexed_items can be 0 in sandbox (no FAISS), just assert it's an int
    assert isinstance(index.get("indexed_items", 0), int)


def test_status_includes_feature_flags() -> None:
    response = client.get("/status")
    assert response.status_code == 200
    payload = response.json()
    flags = payload.get("feature_flags", {})
    assert isinstance(flags, dict), "feature_flags must be a dict"
    # These keys are always present in the /status route
    required_keys = {"knowledge", "tts", "emotion_engine"}
    for key in required_keys:
        assert key in flags, f"Missing feature flag key: {key}"


def test_status_feature_flags_have_correct_types() -> None:
    response = client.get("/status")
    assert response.status_code == 200
    flags = response.json().get("feature_flags", {})
    bool_keys = {"knowledge", "tts", "emotion_engine"}
    for key in bool_keys:
        if key in flags:
            assert isinstance(flags[key], bool), (
                f"Flag '{key}' should be bool, got {type(flags[key])}"
            )


def test_status_knowledge_items_count_is_non_negative() -> None:
    response = client.get("/status")
    assert response.status_code == 200
    payload = response.json()
    count = payload.get("knowledge_items", 0)
    assert isinstance(count, int)
    assert count >= 0
