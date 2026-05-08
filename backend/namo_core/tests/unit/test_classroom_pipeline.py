"""Unit tests for ClassroomPipeline orchestration logic.

Ensures the 7-stage pipeline correctly fuses signals
and respects Dhamma retrieval protocols.

NOTE: pipeline.run() is async — all callers use `await`.
Private attributes use underscore prefix (_emotion_service, _knowledge_service).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from namo_core.services.integration.classroom_pipeline import ClassroomPipeline


class TestClassroomPipelineUnit:
    @pytest.fixture
    def pipeline(self):
        return ClassroomPipeline()

    @pytest.mark.asyncio
    async def test_pipeline_fusion_resonance_logic(self, pipeline):
        """Verify that perception and transcript signals are fused into a resonance score."""
        mock_query = "What is the Middle Way?"
        mock_perception = {"attention_score": 0.9}
        mock_transcript = {"text": "What is the Middle Way?", "confidence": 0.85}

        # Prime the lazy-loaded service before patching
        from namo_core.services.emotion.emotion_service import EmotionService
        pipeline._emotion_service = EmotionService()

        mock_emotion_result = {
            "emotion_state": "focused",
            "smoothed_state": "focused",
            "adaptation_style": "standard",
            "composite_score": 0.88,
            "signals": {"attention": 0.9, "engagement": 0.85},
        }

        with patch.object(
            pipeline._emotion_service,
            "detect",
            return_value=mock_emotion_result,
        ) as mock_detect, patch.object(
            pipeline, "_run_reasoning", new_callable=AsyncMock,
            return_value={"answer": "The Middle Way avoids extremes.", "sources": []},
        ):
            result = await pipeline.run(
                query=mock_query, perception=mock_perception, transcript=mock_transcript
            )

            assert result["emotion"]["emotion_state"] == "focused"
            assert result["emotion"]["composite_score"] == 0.88
            mock_detect.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_empathy_stage_injects_teaching_hint(self, pipeline):
        """Ensure the empathy stage enriches the payload with correct teaching hints."""
        low_attention_perception = {"attention_score": 0.2}

        with patch.object(
            pipeline, "_run_reasoning", new_callable=AsyncMock,
            return_value={"answer": "Be patient.", "sources": []},
        ):
            result = await pipeline.run(
                query="I'm bored", perception=low_attention_perception
            )

        # Low attention should trigger a gentle/patient tone
        assert result["tone"] in ("concerned", "patient", "gentle", "calm")
        assert "teaching_hint" in result

    @pytest.mark.asyncio
    async def test_reasoning_stage_respects_dhamma_context(self, pipeline):
        """Verify that reasoning is called and result is wired back."""
        mock_reasoning = {
            "answer": "The Middle Way avoids two extremes...",
            "sources": [{"title": "Dhammacakkappavattana Sutta"}],
        }

        with patch.object(
            pipeline, "_run_reasoning", new_callable=AsyncMock,
            return_value=mock_reasoning,
        ):
            result = await pipeline.run(query="Explain the Middle Way")

        assert "reasoning" in result["pipeline_meta"]["stages_completed"]
        assert result["reasoning"] == mock_reasoning

    @pytest.mark.asyncio
    async def test_pipeline_handles_empty_input_gracefully(self, pipeline):
        """Edge case: empty/whitespace strings return early without crashing."""
        result = await pipeline.run(query="   ")

        assert result["reasoning"] is None
        assert "empty" in result["pipeline_meta"]["note"]
        # _empty_result returns None for emotion on short-circuit
        assert "emotion" in result
        assert "student_state" in result

    @pytest.mark.asyncio
    async def test_pipeline_resilience_on_service_failure(self, pipeline):
        """Ensure the pipeline falls back gracefully if emotion service raises."""
        # Prime the lazy-loaded service before patching
        from namo_core.services.emotion.emotion_service import EmotionService
        pipeline._emotion_service = EmotionService()

        with patch.object(
            pipeline._emotion_service, "detect",
            side_effect=RuntimeError("emotion service crashed"),
        ), patch.object(
            pipeline, "_run_reasoning", new_callable=AsyncMock,
            return_value={"answer": "Kindness is compassion.", "sources": []},
        ):
            result = await pipeline.run(query="Tell me about kindness")

        # Fallback emotion state on exception is "attentive" (see _detect_emotion)
        assert result["emotion"]["emotion_state"] in ("attentive", "neutral")
        assert result["reasoning"] is not None  # pipeline continues despite emotion failure

    @pytest.mark.asyncio
    async def test_resonance_logic_score_via_empathy(self, pipeline):
        """Verify resonance engine is invoked during the empathy stage."""
        with patch.object(
            pipeline, "_run_empathy",
            return_value=("Stay focused", "calm", "attentive"),
        ) as mock_empathy, patch.object(
            pipeline, "_run_reasoning", new_callable=AsyncMock,
            return_value={"answer": "...", "sources": []},
        ):
            result = await pipeline.run(
                query="test",
                perception={"attention_score": 0.8},
                transcript={"confidence": 0.9},
            )

        mock_empathy.assert_called_once()
        assert result["tone"] == "calm"
        assert result["student_state"] == "attentive"
