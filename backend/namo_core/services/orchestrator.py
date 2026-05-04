"""
orchestrator.py — Central Nervous System (Full-Loop Pipeline)
STT → Emotion → RAG+Reasoning → TTS

Fully async: CPU-bound steps (STT, emotion, FAISS, TTS) run via asyncio.to_thread()
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from pathlib import Path

from namo_core.config.settings import get_settings
from namo_core.utils.text_formatter import format_diarization

logger = logging.getLogger(__name__)


class OrchestratorSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._emotion_analyzer = None
            cls._instance._reasoner = None
            cls._instance._stt = None
        return cls._instance

    @property
    def emotion_analyzer(self):
        if self._emotion_analyzer is None:
            logger.info("[Lazy-Load] Loading TextEmotionAnalyzer...")
            t0 = time.perf_counter()
            try:
                from namo_core.modules.emotion.detector import TextEmotionAnalyzer

                self._emotion_analyzer = TextEmotionAnalyzer()
                logger.info(
                    f"[Lazy-Load] TextEmotionAnalyzer loaded in {time.perf_counter() - t0:.2f}s"
                )
            except Exception as exc:
                logger.warning("Failed to load Emotion Analyzer: %s", exc)
                self._emotion_analyzer = None
        return self._emotion_analyzer

    @property
    def reasoner(self):
        if self._reasoner is None:
            logger.info("[Lazy-Load] Loading Reasoner (FAISS + embeddings)...")
            t0 = time.perf_counter()
            try:
                from namo_core.api.routes.reasoning import get_reasoner

                self._reasoner = get_reasoner()
                logger.info(
                    f"[Lazy-Load] Reasoner loaded in {time.perf_counter() - t0:.2f}s"
                )
            except Exception as exc:
                logger.warning("Failed to load Reasoner: %s", exc)
                self._reasoner = None
        return self._reasoner

    @property
    def stt(self):
        if self._stt is None:
            settings = get_settings()
            if not settings.enable_speech:
                logger.info("[Lazy-Load] Speech module is disabled by settings.")
                return None

            logger.info("[Lazy-Load] Loading Whisper STT...")
            t0 = time.perf_counter()
            try:
                from namo_core.modules.speech.transcriber import FasterWhisperTranscriber

                self._stt = FasterWhisperTranscriber(
                    model_name=settings.speech_model, language=settings.speech_language
                )
                logger.info(f"[Lazy-Load] STT loaded in {time.perf_counter() - t0:.2f}s")
            except Exception as exc:
                logger.warning("Failed to load STT: %s", exc)
                self._stt = None
        return self._stt

    def initialize(self):
        """No-op method kept for backward compatibility.
        All components use lazy loading via properties.
        Models are loaded on-demand when first accessed.
        """
        logger.info("OrchestratorSingleton ready (lazy loading mode enabled)")

    async def run_full_loop(
        self,
        *,
        text: str | None = None,
        audio_path: str | None = None,
        session_id: str = "default",
        voice: str | None = None,
    ) -> dict:
        settings = get_settings()
        tts_voice = voice or settings.tts_voice

        self.initialize()

        t_total = time.perf_counter()
        timings: dict[str, float] = {}
        stt_text = text or ""

        # ── 1. STT ────────────────────────────────────────────────────────
        stt_result: dict = {}
        if not stt_text and audio_path and self.stt:
            t0 = time.perf_counter()
            try:
                stt_result = await asyncio.to_thread(self.stt.transcribe_file, audio_path)
                stt_text = stt_result.get("text", "")
            except Exception as exc:
                logger.warning("STT failed: %s", exc)
                stt_text = ""
            timings["stt_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        if not stt_text:
            if audio_path and not self.stt:
                logger.warning("STT service is not available. Cannot process audio.")
            return {"error": "No input text or STT result", "latency_ms": {}}

        raw_stt_text = stt_text

        # ── Phase 12: Speaker Diarization Formatting ──────────────────────────
        if diarization_data := stt_result.get("diarization"):
            if formatted_text := format_diarization(diarization_data):
                stt_text = formatted_text

        # ── 2. Emotion Detection ──────────────────────────────────────────
        t0 = time.perf_counter()
        emotion_result = {"emotion": "neutral", "confidence": 0.5}
        teaching_hint = ""
        if self.emotion_analyzer:
            try:
                from namo_core.engines.empathy.engine import EmpathyEngine
                emotion_result = await asyncio.to_thread(self.emotion_analyzer.analyze, raw_stt_text)
                teaching_hint = EmpathyEngine.modifier_from_text_emotion(emotion_result["emotion"])
            except Exception as exc:
                logger.warning("Emotion analysis failed: %s", exc)
        timings["emotion_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        # ── 3. RAG + Reasoning (FAISS search + LLM call) ─────────────────
        t0 = time.perf_counter()
        answer = "[reasoning service unavailable]"
        if self.reasoner:
            try:
                reason = await asyncio.to_thread(
                    self.reasoner.chat,
                    messages=[{"role": "user", "content": stt_text}],
                    teaching_hint=teaching_hint,
                    session_id=session_id,
                )
                answer = reason.get("answer", "")
            except Exception as exc:
                logger.error("Reasoning failed: %s", exc)
                answer = f"[reasoning error: {exc}]"
        timings["reasoning_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        # ── 4. TTS ────────────────────────────────────────────────────────
        t0 = time.perf_counter()
        audio_b64 = None
        audio_fmt = "mp3"
        try:
            from namo_core.modules.tts.providers.edge_tts_provider import EdgeTTSProvider

            tts_provider = EdgeTTSProvider(default_voice=tts_voice)
            tts_result = await asyncio.to_thread(tts_provider.synthesize, answer, voice=tts_voice)
            audio_b64 = tts_result.get("audio_base64")
            audio_fmt = tts_result.get("audio_format", "mp3")
        except Exception as exc:
            logger.warning("TTS failed: %s", exc)
        timings["tts_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        timings["total_ms"] = round((time.perf_counter() - t_total) * 1000, 1)

        return {
            "stt_text": stt_text,
            "emotion": emotion_result.get("emotion"),
            "teaching_hint": teaching_hint,
            "answer": answer,
            "audio_base64": audio_b64,
            "audio_format": audio_fmt,
            "latency_ms": timings,
        }


# Global Singleton Instance
orchestrator = OrchestratorSingleton()


async def run_full_loop(
    *,
    text: str | None = None,
    audio_path: str | None = None,
    session_id: str = "default",
    voice: str | None = None,
) -> dict:
    """รัน Full Pipeline: (Audio|Text) → STT → Emotion → Reasoner → TTS"""
    return await orchestrator.run_full_loop(
        text=text,
        audio_path=audio_path,
        session_id=session_id,
        voice=voice,
    )
