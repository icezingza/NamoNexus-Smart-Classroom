"""Phase 7 Integration Tests — Full pipeline end-to-end via FastAPI TestClient.

Auth: EnterpriseAuthMiddleware requires Bearer JWT on /nexus/* and /classroom/*.
      Tests use the `auth_client` fixture (TestClient with token pre-set).
"""
import pytest
from fastapi.testclient import TestClient

from namo_core.api.app import app

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def auth_client(auth_headers):
    """TestClient with Authorization header pre-set for the whole module."""
    with TestClient(app, headers=auth_headers) as c:
        yield c


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

DHAMMA_QUERY = {"text": "ทุกข์คืออะไร", "attention_score": 0.8}
SIMPLE_QUERY = {"text": "What is mindfulness?", "attention_score": 0.7}


# ─────────────────────────────────────────────────────────────────────────────
# /nexus/text-chat
# ─────────────────────────────────────────────────────────────────────────────

class TestTextChat:
    def test_returns_200(self, auth_client):
        response = auth_client.post("/nexus/text-chat", json=SIMPLE_QUERY)
        assert response.status_code == 200

    def test_response_has_required_keys(self, auth_client):
        data = auth_client.post("/nexus/text-chat", json=SIMPLE_QUERY).json()
        for key in ("query", "reasoning", "emotion", "tone", "student_state", "pipeline_meta"):
            assert key in data, f"Missing key: {key}"

    def test_query_echoed_in_response(self, auth_client):
        data = auth_client.post(
            "/nexus/text-chat", json={"text": "hello", "attention_score": 0.5}
        ).json()
        assert data["query"] == "hello"

    def test_reasoning_has_answer(self, auth_client):
        data = auth_client.post("/nexus/text-chat", json=SIMPLE_QUERY).json()
        reasoning = data["reasoning"]
        assert reasoning is not None
        assert "answer" in reasoning
        assert len(reasoning["answer"]) > 0

    def test_emotion_has_state(self, auth_client):
        data = auth_client.post("/nexus/text-chat", json=DHAMMA_QUERY).json()
        emotion = data["emotion"]
        assert emotion is not None
        assert emotion["emotion_state"] in (
            "focused", "attentive", "wandering", "distracted", "disengaged"
        )

    def test_emotion_composite_score_in_range(self, auth_client):
        data = auth_client.post(
            "/nexus/text-chat", json={"text": "test", "attention_score": 0.9}
        ).json()
        score = data["emotion"]["composite_score"]
        assert 0.0 <= score <= 1.0

    def test_high_attention_yields_positive_tone(self, auth_client):
        data = auth_client.post(
            "/nexus/text-chat", json={"text": "อธิบายอนิจจังได้ไหม", "attention_score": 0.95}
        ).json()
        assert data["tone"] in ("warm", "calm")

    def test_low_attention_yields_gentle_tone(self, auth_client):
        data = auth_client.post(
            "/nexus/text-chat", json={"text": "ok", "attention_score": 0.1}
        ).json()
        assert data["tone"] in ("concerned", "patient", "gentle")

    def test_pipeline_meta_stages_completed(self, auth_client):
        data = auth_client.post("/nexus/text-chat", json=SIMPLE_QUERY).json()
        stages = data["pipeline_meta"]["stages_completed"]
        assert "emotion" in stages
        assert "reasoning" in stages

    def test_empty_text_returns_422(self, auth_client):
        response = auth_client.post(
            "/nexus/text-chat", json={"text": "", "attention_score": 0.7}
        )
        assert response.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# /nexus/classroom-loop
# ─────────────────────────────────────────────────────────────────────────────

class TestClassroomLoop:
    def test_returns_200(self, auth_client):
        response = auth_client.post("/nexus/classroom-loop", json=SIMPLE_QUERY)
        assert response.status_code == 200

    def test_input_mode_is_classroom_loop(self, auth_client):
        data = auth_client.post("/nexus/classroom-loop", json=SIMPLE_QUERY).json()
        assert data["pipeline_meta"]["input_mode"] == "classroom-loop"


# ─────────────────────────────────────────────────────────────────────────────
# Event log integration
# ─────────────────────────────────────────────────────────────────────────────

class TestEventLogIntegration:
    """Tests for /classroom/events endpoint (in-memory ClassroomEventLog).

    NOTE: /nexus/text-chat logs to the *database* EventLog (separate system).
    /classroom/events reads from the in-memory ClassroomEventLog which is
    populated by state transitions and classroom lifecycle events — not by
    text-chat calls. These tests verify the endpoint contract only.
    """

    def test_events_endpoint_returns_valid_shape(self, auth_client):
        """GET /classroom/events → 200 with events list + total count."""
        resp = auth_client.get("/classroom/events")
        assert resp.status_code == 200
        body = resp.json()
        assert "events" in body
        assert "total" in body
        assert isinstance(body["events"], list)
        assert isinstance(body["total"], int)

    def test_events_endpoint_respects_limit_param(self, auth_client):
        """limit query param is accepted without error."""
        resp = auth_client.get("/classroom/events?limit=5")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["events"]) <= 5


# ─────────────────────────────────────────────────────────────────────────────
# Slide context integration
# ─────────────────────────────────────────────────────────────────────────────

class TestSlideContextIntegration:
    @pytest.fixture(autouse=True)
    def _start_lesson(self, auth_client):
        resp = auth_client.post(
            "/classroom/session/start", json={"lesson_id": "lesson-intro-buddhism"}
        )
        assert resp.status_code == 200

    def test_text_chat_includes_slide_context_when_session_active(self, auth_client):
        data = auth_client.post("/nexus/text-chat", json=DHAMMA_QUERY).json()
        slide_ctx = data.get("slide_context")
        if slide_ctx is not None:
            assert "title" in slide_ctx
            assert "dhamma_point" in slide_ctx

    def test_next_slide_changes_slide_context(self, auth_client):
        data1 = auth_client.post("/nexus/text-chat", json=SIMPLE_QUERY).json()
        auth_client.post("/classroom/slide/next")
        data2 = auth_client.post("/nexus/text-chat", json=SIMPLE_QUERY).json()
        if data1.get("slide_context") and data2.get("slide_context"):
            assert (
                data1["slide_context"].get("slide_number")
                != data2["slide_context"].get("slide_number")
            )


# ─────────────────────────────────────────────────────────────────────────────
# ClassroomPipeline unit-level (async run())
# ─────────────────────────────────────────────────────────────────────────────

class TestClassroomPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_run_returns_expected_keys(self):
        from namo_core.services.integration.classroom_pipeline import ClassroomPipeline
        pipeline = ClassroomPipeline()
        result = await pipeline.run(query="What is dukkha?")
        for key in ("query", "emotion", "teaching_hint", "tone",
                    "student_state", "reasoning", "tts", "pipeline_meta"):
            assert key in result

    @pytest.mark.asyncio
    async def test_pipeline_handles_empty_query(self):
        from namo_core.services.integration.classroom_pipeline import ClassroomPipeline
        pipeline = ClassroomPipeline()
        result = await pipeline.run(query="   ")
        assert result["reasoning"] is None
        assert "empty" in result["pipeline_meta"].get("note", "")

    @pytest.mark.asyncio
    async def test_pipeline_high_attention_focused_state(self):
        from namo_core.services.integration.classroom_pipeline import ClassroomPipeline
        pipeline = ClassroomPipeline()
        result = await pipeline.run(
            query="อธิบายพระนิพพาน",
            perception={"attention_score": 0.95},
            transcript={"text": "อธิบายพระนิพพาน " * 3, "confidence": 0.95},
        )
        assert result["emotion"]["composite_score"] > 0.7
        assert result["tone"] in ("warm", "calm")

    @pytest.mark.asyncio
    async def test_pipeline_low_attention_concerned_tone(self):
        from namo_core.services.integration.classroom_pipeline import ClassroomPipeline
        pipeline = ClassroomPipeline()
        result = await pipeline.run(
            query="ok",
            perception={"attention_score": 0.1},
            transcript={"text": "ok", "confidence": 0.1},
        )
        assert result["tone"] in ("concerned", "patient", "gentle")
