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


def test_status_includes_knowledge_index_with_tfidf_plus() -> None:
    response = client.get("/status")
    assert response.status_code == 200
    payload = response.json()
    index = payload["knowledge_index"]
    assert index["backend"] == "tf-idf-plus"
    assert index["indexed_items"] >= 20, (
        f"Expected at least 20 indexed items (expanded corpus), got {index['indexed_items']}"
    )


def test_status_includes_feature_flags() -> None:
    response = client.get("/status")
    assert response.status_code == 200
    payload = response.json()
    flags = payload["feature_flags"]

    # All expected flag keys must be present
    required_keys = {"speech", "vision", "real_devices", "llm_intent", "knowledge", "empathy_engine", "tts", "device_mode"}
    for key in required_keys:
        assert key in flags, f"Missing feature flag key: {key}"


def test_status_feature_flags_have_correct_types() -> None:
    response = client.get("/status")
    assert response.status_code == 200
    flags = response.json()["feature_flags"]

    expected_flags = {
        "device_mode",
        "speech",
        "vision",
        "llm_intent",
        "knowledge",
        "empathy_engine",
        "tts",
        "classroom_control",
    }
    # Ensure all expected flags are present
    for key in expected_flags:
        assert key in flags, f"Missing feature flag key: {key}"

    bool_keys = {"speech", "vision", "llm_intent", "knowledge", "empathy_engine", "tts", "classroom_control"}
    for key in bool_keys:
        assert isinstance(flags[key], bool), f"Flag '{key}' should be bool, got {type(flags[key])}"
    assert isinstance(flags["device_mode"], str)


def test_status_knowledge_items_count_reflects_expanded_corpus() -> None:
    response = client.get("/status")
    assert response.status_code == 200
    payload = response.json()
    # We have 15 suttas + 2 md files + 8 lessons = 25
    assert payload["knowledge_items"] >= 20
