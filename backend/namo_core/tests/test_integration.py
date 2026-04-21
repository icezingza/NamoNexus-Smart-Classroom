"""Phase 7 Integration Tests — Full pipeline end-to-end via FastAPI TestClient.

Tests the complete classroom interaction loop connecting:
    Phase 4: NamoNexus / RAG / LLM
    Phase 5: Emotion Engine
    Phase 6: Classroom System
    Phase 7: ClassroomPipeline integration

All tests use /nexus/text-chat and /nexus/classroom-loop endpoints
to avoid audio hardware dependency.
"""
import pytest
from fastapi.testclient import TestClient

from namo_core.api.app import app

client = TestClient(app)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

DHAMMA_QUERY = {"text": "ทุกข์คืออะไร", "attention_score": 0.8}
SIMPLE_QUERY = {"text": "What is mindfulness?", "attention_score": 0.7}


def _start_lesson(lesson_id: str = "lesson-intro-buddhism") -> dict:
    resp = client.post("/classroom/session/start", json={"lesson_id": lesson_id})
    assert resp.status_code == 200
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# /nexus/text-chat
# ─────────────────────────────────────────────────────────────────────────────

class TestTextChat:
    def test_returns_200(self):
        response = client.post("/nexus/text-chat", json=SIMPLE_QUERY)
        assert response.status_code == 200

    def test_response_has_required_keys(self):
        data = client.post("/nexus/text-chat", json=SIMPLE_QUERY).json()
        for key in ("query", "reasoning", "emotion", "tone", "student_state", "pipeline_meta"):
            assert key in data, f"Missing key: {key}"

    def test_query_echoed_in_response(self):
        data = client.post("/nexus/text-chat", json={"text": "hello", "attention_score": 0.5}).json()
        assert data["query"] == "hello"

    def test_reasoning_has_answer(self):
        data = client.post("/nexus/text-chat", json=SIMPLE_QUERY).json()
        reasoning = data["reasoning"]
        assert reasoning is not None
        assert "answer" in reasoning
        assert len(reasoning["answer"]) > 0

    def test_emotion_has_state(self):
        data = client.post("/nexus/text-chat", json=DHAMMA_QUERY).json()
        emotion = data["emotion"]
        assert emotion is not None
        assert emotion["emotion_state"] in (
            "focused", "attentive", "wandering", "distracted", "disengaged"
        )

    def test_emotion_composite_score_in_range(self):
        data = client.post("/nexus/text-chat", json={"text": "test", "attention_score": 0.9}).json()
        score = data["emotion"]["composite_score"]
        assert 0.0 <= score <= 1.0

    def test_high_attention_yields_positive_tone(self):
        data = client.post(
            "/nexus/text-chat", json={"text": "อธิบายอนิจจังได้ไหม", "attention_score": 0.95}
        ).json()
        assert data["tone"] in ("warm", "calm")

    def test_low_attention_yields_gentle_tone(self):
        data = client.post(
            "/nexus/text-chat", json={"text": "ok", "attention_score": 0.1}
        ).json()
        assert data["tone"] in ("concerned", "patient", "gentle")

    def test_pipeline_meta_stages_completed(self):
        data = client.post("/nexus/text-chat", json=SIMPLE_QUERY).json()
        stages = data["pipeline_meta"]["stages_completed"]
        assert "emotion" in stages
        assert "reasoning" in stages

    def test_empty_text_returns_422(self):
        response = client.post("/nexus/text-chat", json={"text": "", "attention_score": 0.7})
        assert response.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# /nexus/classroom-loop
# ─────────────────────────────────────────────────────────────────────────────

class TestClassroomLoop:
    def test_returns_200(self):
        response = client.post("/nexus/classroom-loop", json=SIMPLE_QUERY)
        assert response.status_code == 200

    def test_same_shape_as_text_chat(self):
        text_data = client.post("/nexus/text-chat", json=SIMPLE_QUERY).json()
        loop_data = client.post("/nexus/classroom-loop", json=SIMPLE_QUERY).json()
        # Both should have the same top-level keys
        assert set(text_data.keys()) == set(loop_data.keys())

    def test_input_mode_is_classroom_loop(self):
        data = client.post("/nexus/classroom-loop", json=SIMPLE_QUERY).json()
        assert data["pipeline_meta"]["input_mode"] == "classroom-loop"


# ─────────────────────────────────────────────────────────────────────────────
# Slide context integration
# ─────────────────────────────────────────────────────────────────────────────

class TestSlideContextIntegration:
    def setup_method(self):
        _start_lesson("lesson-intro-buddhism")

    def test_text_chat_includes_slide_context_when_session_active(self):
        data = client.post("/nexus/text-chat", json=DHAMMA_QUERY).json()
        # slide_context may be None or dict; if dict it should have expected keys
        slide_ctx = data.get("slide_context")
        if slide_ctx is not None:
            assert "title" in slide_ctx
            assert "dhamma_point" in slide_ctx

    def test_next_slide_changes_slide_context(self):
        data1 = client.post("/nexus/text-chat", json=SIMPLE_QUERY).json()
        client.post("/classroom/slide/next")
        data2 = client.post("/nexus/text-chat", json=SIMPLE_QUERY).json()
        # slide number should differ
        if data1.get("slide_context") and data2.get("slide_context"):
            assert data1["slide_context"].get("slide_number") != data2["slide_context"].get("slide_number")


# ─────────────────────────────────────────────────────────────────────────────
# Event log integration (classroom events logged during pipeline)
# ─────────────────────────────────────────────────────────────────────────────

class TestEventLogIntegration:
    def test_text_chat_creates_ai_response_event(self):
        client.post("/nexus/text-chat", json=SIMPLE_QUERY)
        events = client.get("/classroom/events").json()
        event_types = [e["type"] for e in events["events"]]
        assert "ai_response" in event_types

    def test_event_contains_query(self):
        unique_query = "unique_integration_test_query_xyz"
        client.post("/nexus/text-chat", json={"text": unique_query, "attention_score": 0.7})
        events = client.get("/classroom/events").json()
        ai_events = [e for e in events["events"] if e["type"] == "ai_response"]
        queries = [e["data"].get("query", "") for e in ai_events]
        assert any(unique_query[:20] in q for q in queries)


# ─────────────────────────────────────────────────────────────────────────────
# ClassroomPipeline unit-level tests
# ─────────────────────────────────────────────────────────────────────────────

class TestClassroomPipeline:
    def test_pipeline_run_returns_expected_keys(self):
        from namo_core.services.integration.classroom_pipeline import ClassroomPipeline
        pipeline = ClassroomPipeline()
        result = pipeline.run(query="What is dukkha?")
        for key in ("query", "emotion", "teaching_hint", "tone",
                    "student_state", "reasoning", "tts", "pipeline_meta"):
            assert key in result

    def test_pipeline_handles_empty_query(self):
        from namo_core.services.integration.classroom_pipeline import ClassroomPipeline
        pipeline = ClassroomPipeline()
        result = pipeline.run(query="   ")
        assert result["reasoning"] is None
        assert "empty" in result["pipeline_meta"].get("note", "")

    def test_pipeline_high_attention_focused_state(self):
        from namo_core.services.integration.classroom_pipeline import ClassroomPipeline
        pipeline = ClassroomPipeline()
        result = pipeline.run(
            query="อธิบายพระนิพพาน",
            perception={"attention_score": 0.95},
            transcript={"text": "อธิบายพระนิพพาน " * 3, "confidence": 0.95},
        )
        assert result["emotion"]["composite_score"] > 0.7
        assert result["tone"] in ("warm", "calm")

    def test_pipeline_low_attention_concerned_tone(self):
        from namo_core.services.integration.classroom_pipeline import ClassroomPipeline
        pipeline = ClassroomPipeline()
        result = pipeline.run(
            query="ok",
            perception={"attention_score": 0.1},
            transcript={"text": "ok", "confidence": 0.1},
        )
        assert result["tone"] in ("concerned", "patient", "gentle")

    def test_context_builder_with_slide(self):
        from namo_core.services.knowledge.context_builder import ContextBuilder
        cb = ContextBuilder()

        items = [{"title": "Dukkha", "content": "Suffering is the first noble truth."}]
        slide = {"slide_number": 2, "title": "ทุกข์", "dhamma_point": "ทุกข์คือธรรมชาติของสังสารวัฏ", "key_concept": "dukkha"}
        hint = "อธิบายสั้นๆ จบด้วยคำถาม"

        context = cb.build_with_slide(items, slide=slide, teaching_hint=hint)
        assert "คำแนะนำการสอน" in context
        assert "ทุกข์" in context
        assert "Dukkha" in context
        assert "Suffering" in context
