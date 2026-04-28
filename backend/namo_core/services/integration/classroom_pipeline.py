"""ClassroomPipeline — Phase 7: Unified integration of all subsystems.

Connects Phase 4 (NamoNexus / RAG / LLM), Phase 5 (Emotion Engine),
and Phase 6 (Classroom System) into a single orchestrated pipeline.

Full pipeline flow:
    text input (from STT or direct text)
      ↓
    [Semantic Cache] Check for similar cached responses (threshold 0.85)
      ↓
    [Phase 5] EmotionService.detect(perception, transcript)
      → composite_score, smoothed_state
      ↓
    [Phase 5] EmpathyEngine.process(payload)
      → tone, teaching_hint (Thai instruction for LLM)
      ↓
    [Phase 6] SlideController.content()
      → current slide title, body, dhamma_point, key_concept
      ↓
    [Phase 4] KnowledgeService.search(query)
      → FAISS/TF-IDF knowledge items
      ↓
    Context Assembly:
      teaching_hint + slide context + knowledge context → combined_context
      ↓
    [Phase 4] ReasoningService.explain(query, teaching_hint)
      → LLM response (answer, sources)
      ↓
    Cache Result for future semantic matches
      ↓
    [Phase 6] ClassroomService.log event + state transition
      ↓
    Optional TTS synthesis
      ↓
    PipelineResult dict
"""

from __future__ import annotations

import asyncio
import logging
from asyncio import to_thread

from namo_core.services.knowledge.semantic_cache import query_cache

logger = logging.getLogger(__name__)


class ClassroomPipeline:
    """Unified pipeline integrating all Namo Core subsystems.

    Instantiated once and reused across requests. All heavy services
    are lazy-loaded on first call to avoid import-time failures when
    optional dependencies (FAISS, Whisper) are absent.
    """

    def __init__(self) -> None:
        self._emotion_service = None
        self._empathy_engine = None
        self._resonance_engine = None
        self._knowledge_service = None
        self._reasoning_service = None
        self._slide_controller = None
        self._classroom_service = None
        self._tts_synthesizer = None
        self._vision_analyzer = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        query: str,
        transcript: dict | None = None,
        perception: dict | None = None,
        speak: bool = False,
        voice: str | None = None,
    ) -> dict:
        """Execute the full classroom interaction pipeline (async).

        Args:
            query: Student's question or text input (from STT or direct).
            transcript: Optional STT transcript dict (confidence, text, …).
                        If absent, synthesised from query text.
            perception: Optional vision signals dict (attention_score, …).
                        If absent, defaults to neutral 0.7 attention.
            speak: If True, synthesise TTS response.
            voice: Optional TTS voice override.

        Returns:
            PipelineResult dict with keys:
                emotion       – emotion detection result
                teaching_hint – EmpathyEngine adaptation instruction
                slide_context – current slide content summary
                reasoning     – LLM response with sources
                tts           – TTS result (None if speak=False)
                pipeline_meta – metadata about each stage
        """
        query = query.strip()
        if not query:
            return _empty_result("empty query")

        # Normalise inputs
        transcript = transcript or {"text": query, "confidence": 0.5}
        perception = perception or {"attention_score": 0.7, "engagement": "neutral"}

        meta: dict = {"stages_completed": []}

        # ── Stage 1: Emotion Detection ─────────────────────────────────────────
        emotion_result = self._detect_emotion(perception, transcript)
        meta["stages_completed"].append("emotion")
        logger.debug(
            "emotion: %s (composite=%.3f)",
            emotion_result["smoothed_state"],
            emotion_result["composite_score"],
        )

        # ── Stage 2: Resonance + EmpathyEngine → teaching_hint ────────────────
        teaching_hint, tone, student_state = self._run_empathy(
            perception=perception,
            transcript=transcript,
            emotion_state=emotion_result["emotion_state"],
        )
        meta["stages_completed"].append("empathy")
        meta["tone"] = tone
        meta["student_state"] = student_state

        # ── Stage 3: Current Slide Context ────────────────────────────────────
        slide_context = self._get_slide_context()
        if slide_context:
            meta["stages_completed"].append("slide_context")

        # ── Stage 4: Knowledge RAG Search ─────────────────────────────────────
        reasoning_result = await self._run_reasoning(
            query, teaching_hint, slide_context
        )
        meta["stages_completed"].append("reasoning")
        logger.debug("reasoning sources: %d", len(reasoning_result.get("sources", [])))

        # ── Stage 5: Log event + transition assistant state ────────────────────
        self._log_interaction(query, emotion_result["smoothed_state"])
        meta["stages_completed"].append("event_logged")

        # ── Stage 6: TTS (optional) ───────────────────────────────────────────
        tts_result: dict | None = None
        if speak:
            tts_result = await self._synthesize(
                reasoning_result.get("answer", ""), voice
            )
            if tts_result:
                meta["stages_completed"].append("tts")

        return {
            "query": query,
            "emotion": emotion_result,
            "teaching_hint": teaching_hint,
            "tone": tone,
            "student_state": student_state,
            "slide_context": slide_context,
            "reasoning": reasoning_result,
            "tts": tts_result,
            "pipeline_meta": meta,
        }

    # ------------------------------------------------------------------
    # Private stage helpers
    # ------------------------------------------------------------------

    def _detect_emotion(self, perception: dict, transcript: dict) -> dict:
        """Run EmotionService and return detection result."""
        if self._emotion_service is None:
            from namo_core.services.emotion.emotion_service import EmotionService

            self._emotion_service = EmotionService()

        try:
            return self._emotion_service.detect(
                perception=perception, transcript=transcript
            )
        except Exception as exc:
            logger.warning("Emotion detection failed: %s", exc)
            return {
                "emotion_state": "attentive",
                "smoothed_state": "attentive",
                "adaptation_style": "standard",
                "composite_score": 0.6,
                "signals": {},
            }

    def _run_empathy(
        self, perception: dict, transcript: dict, emotion_state: str
    ) -> tuple[str, str, str]:
        """Run ResonanceEngine + EmpathyEngine and return (teaching_hint, tone, student_state)."""
        if self._resonance_engine is None:
            from namo_core.engines.resonance.engine import ResonanceEngine

            self._resonance_engine = ResonanceEngine()
        if self._empathy_engine is None:
            from namo_core.engines.empathy.engine import EmpathyEngine

            self._empathy_engine = EmpathyEngine()

        try:
            payload = {"perception": perception, "transcript": transcript}
            payload = self._resonance_engine.process(payload)
            payload["emotion_state"] = emotion_state
            payload = self._empathy_engine.process(payload)
            return (
                payload.get("teaching_hint", ""),
                payload.get("tone", "calm"),
                payload.get("student_state", "attentive"),
            )
        except Exception as exc:
            logger.warning("Empathy processing failed: %s", exc)
            return "", "calm", "attentive"

    def _get_slide_context(self) -> dict | None:
        """Fetch current slide content from SlideController."""
        try:
            if self._slide_controller is None:
                from namo_core.modules.classroom.slide_controller import SlideController

                self._slide_controller = SlideController()

            slide = self._slide_controller.content()
            # Only return if we have actual content (not a fallback empty slide)
            if slide.get("dhamma_point") or slide.get("key_concept") not in ("", None):
                return {
                    "slide_number": slide.get("slide_number"),
                    "title": slide.get("title", ""),
                    "dhamma_point": slide.get("dhamma_point", ""),
                    "key_concept": slide.get("key_concept", ""),
                    "teaching_note": slide.get("teaching_note", ""),
                }
        except Exception as exc:
            logger.debug("Slide context unavailable: %s", exc)
        return None

    def _build_combined_context(
        self,
        knowledge_context: str,
        teaching_hint: str,
        slide_context: dict | None,
    ) -> str:
        """Assemble the full LLM context from all sources."""
        parts: list[str] = []

        if teaching_hint:
            parts.append(f"[คำแนะนำการสอน: {teaching_hint}]")

        if slide_context:
            slide_summary = (
                f"[สไลด์ปัจจุบัน {slide_context.get('slide_number', '')}: "
                f"{slide_context.get('title', '')} — "
                f"ธรรมะหลัก: {slide_context.get('dhamma_point', '')}]"
            )
            parts.append(slide_summary)

        if knowledge_context:
            parts.append(knowledge_context)

        return "\n\n".join(parts)

    async def _run_reasoning(
        self,
        query: str,
        teaching_hint: str,
        slide_context: dict | None,
    ) -> dict:
        """Run knowledge search and LLM reasoning with combined context (async).

        First checks semantic cache for similar cached responses before
        running full RAG/LLM pipeline. Returns cached response if similarity ≥ threshold.
        """
        # ── Semantic Cache: First gate ────────────────────────────────────────
        cached_response, similarity_score = query_cache.get_cached_response(query)
        if cached_response is not None:
            logger.info(
                f"[Semantic Cache] Returning cached response (similarity: {similarity_score:.2f}) "
                f"— skipping RAG/LLM pipeline"
            )
            return cached_response

        if self._knowledge_service is None:
            from namo_core.services.knowledge.knowledge_service import KnowledgeService

            self._knowledge_service = KnowledgeService()

        if self._reasoning_service is None:
            from namo_core.services.reasoning.reasoner import ReasoningService

            self._reasoning_service = ReasoningService()

        try:
            # Delegate fully to ReasoningService (which handles FAISS + LLM async-natively)
            response = await self._reasoning_service.explain(
                query=query, teaching_hint=teaching_hint
            )

            # ── Cache the response for future semantic matches ─────────────────
            query_cache.add_to_cache(query, response)
            logger.debug("[Semantic Cache] Cached response for: '%s'", query[:80])

            return response
        except Exception as exc:
            import traceback

            logger.error(
                "CRITICAL: Reasoning failed in pipeline: %s\n%s",
                exc,
                traceback.format_exc(),
            )
            return {
                "query": query,
                "answer": f"ขออภัย ระบบไม่สามารถตอบคำถามได้ในขณะนี้: {exc}",
                "sources": [],
                "context": "",
                "provider": "error",
                "model": "fallback-error",
            }

    def _log_interaction(self, query: str, emotion_state: str) -> None:
        """Log the interaction to the classroom event log."""
        try:
            if self._classroom_service is None:
                from namo_core.services.classroom.classroom_service import (
                    ClassroomService,
                )

                self._classroom_service = ClassroomService()

            from namo_core.services.classroom.classroom_event_log import _event_log

            _event_log.log(
                "ai_response",
                {
                    "query": query[:100],
                    "emotion_state": emotion_state,
                },
            )

            # Transition: teaching → listening → responding → teaching
            from namo_core.services.classroom.teaching_state_machine import (
                _state_machine,
            )

            current = _state_machine.current
            if current == "teaching":
                try:
                    _state_machine.transition("listening")
                    _state_machine.transition("responding")
                    _state_machine.transition("teaching")
                except ValueError:
                    pass  # State transitions are best-effort
        except Exception as exc:
            logger.debug("Event logging non-fatal: %s", exc)

    async def _synthesize(self, text: str, voice: str | None) -> dict | None:
        """Synthesize TTS audio for the answer text (async)."""
        if not text:
            return None

        try:
            if self._tts_synthesizer is None:
                from namo_core.modules.tts.synthesizer import SpeechSynthesizer

                self._tts_synthesizer = SpeechSynthesizer()

            return await to_thread(self._tts_synthesizer.speak, text=text, voice=voice)
        except Exception as exc:
            logger.warning("TTS synthesis failed (non-fatal): %s", exc)
            return {"status": "error", "error": str(exc)}


# ── Module-level singleton ─────────────────────────────────────────────────────
# Shared across requests so service instances (EmotionService tracker, etc.)
# persist their rolling state.
_pipeline = ClassroomPipeline()


def get_pipeline() -> ClassroomPipeline:
    """Return the module-level ClassroomPipeline singleton."""
    return _pipeline


def _empty_result(reason: str) -> dict:
    return {
        "query": "",
        "emotion": None,
        "teaching_hint": "",
        "tone": "calm",
        "student_state": "attentive",
        "slide_context": None,
        "reasoning": None,
        "tts": None,
        "pipeline_meta": {"stages_completed": [], "note": reason},
    }
