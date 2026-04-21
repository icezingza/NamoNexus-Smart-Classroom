"""Integration tests for Phase 5 Emotion Engine API endpoint.

Tests the GET /emotion/state FastAPI endpoint end-to-end via TestClient.
"""
import pytest
from fastapi.testclient import TestClient

from namo_core.api.app import app

client = TestClient(app)


class TestEmotionRoute:
    def test_get_emotion_state_returns_200(self):
        response = client.get("/emotion/state")
        assert response.status_code == 200

    def test_response_has_status_ok(self):
        response = client.get("/emotion/state")
        data = response.json()
        assert data["status"] == "ok"

    def test_response_has_emotion_state(self):
        response = client.get("/emotion/state")
        data = response.json()
        assert "emotion_state" in data
        assert data["emotion_state"] in (
            "focused", "attentive", "wandering", "distracted", "disengaged"
        )

    def test_response_has_smoothed_state(self):
        response = client.get("/emotion/state")
        data = response.json()
        assert "smoothed_state" in data
        assert data["smoothed_state"] in (
            "focused", "attentive", "wandering", "distracted", "disengaged"
        )

    def test_response_has_adaptation_style(self):
        response = client.get("/emotion/state")
        data = response.json()
        assert "adaptation_style" in data
        assert data["adaptation_style"] in (
            "detailed", "standard", "concise", "story_based", "reset"
        )

    def test_response_has_composite_score_in_range(self):
        response = client.get("/emotion/state")
        data = response.json()
        assert "composite_score" in data
        assert 0.0 <= data["composite_score"] <= 1.0

    def test_response_has_signals(self):
        response = client.get("/emotion/state")
        data = response.json()
        assert "signals" in data
        signals = data["signals"]
        assert "attention_score" in signals
        assert "speech_confidence" in signals
        assert "speech_energy" in signals

    def test_multiple_calls_return_consistent_structure(self):
        """Repeated calls should always return the same keys."""
        required_keys = {
            "status", "emotion_state", "smoothed_state",
            "adaptation_style", "explanation_pace",
            "composite_score", "signals",
        }
        for _ in range(3):
            response = client.get("/emotion/state")
            assert response.status_code == 200
            data = response.json()
            assert required_keys.issubset(data.keys())
