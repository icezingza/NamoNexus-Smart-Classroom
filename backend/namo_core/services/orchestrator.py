"""
orchestrator.py — Central Nervous System (Full-Loop Pipeline)
STT → Emotion → RAG+Reasoning → TTS

ทุก step ทำงานแบบ sync-safe ใช้ได้ทั้ง HTTP และ WebSocket handler
"""

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path

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
            logger.info("[Lazy-Load] Loading Whisper STT...")
            t0 = time.perf_counter()
            try:
                from namo_core.modules.speech.transcriber import FasterWhisperTranscriber

                self._stt = FasterWhisperTranscriber(model_name="base", language="th")
                logger.info(f"[Lazy-Load] STT loaded in {time.perf_counter() - t0:.2f}s")
            except Exception as exc:
                logger.warning("Failed to load STT: %s", exc)
                self._stt = None
        return self._stt

    def initialize(self, stt_model: str = "tiny", language: str = "th"):
        """No-op method kept for backward compatibility.
        All components use lazy loading via properties.
        Models are loaded on-demand when first accessed.
        """
        logger.info("OrchestratorSingleton ready (lazy loading mode enabled)")

    def run_full_loop(
        self,
        *,
        text: str | None = None,
        audio_path: str | None = None,
        session_id: str = "default",
        voice: str = "th-TH-PremwadeeNeural",
        stt_model: str = "tiny",
        language: str = "th",
    ) -> dict:
        # Initialize heavily-loaded models lazily upon first request
        self.initialize(stt_model=stt_model, language=language)

        t_total = time.perf_counter()
        timings: dict[str, float] = {}
        stt_text = text or ""

        # ── 1. STT ────────────────────────────────────────────────────────
        if not stt_text and audio_path:
            t0 = time.perf_counter()
            try:
                if self.stt:
                    stt_result = self.stt.transcribe_file(audio_path)
                else:
                    from namo_core.modules.speech.transcriber import (
                        FasterWhisperTranscriber,
                    )

                    stt = FasterWhisperTranscriber(
                        model_name=stt_model, language=language
                    )
                    stt_result = stt.transcribe_file(audio_path)
                stt_text = stt_result.get("text", "")
            except Exception as exc:
                logger.warning("STT failed: %s", exc)
                stt_text = ""
            timings["stt_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        if not stt_text:
            return {"error": "No input text or STT result", "latency_ms": {}}

        raw_stt_text = stt_text

        # ── Phase 12: Speaker Diarization Formatting ──────────────────────────
        if "stt_result" in locals() and stt_result.get("diarization"):
            diarization = stt_result["diarization"]
            speaker_blocks = []
            current_speaker = None
            current_words = []
            for item in diarization:
                spk = item.get("speaker_tag")
                word = item.get("word", "")
                if spk != current_speaker:
                    if current_speaker is not None:
                        speaker_blocks.append(f"[ผู้พูดที่ {current_speaker}]: {''.join(current_words).strip()}")
                    current_speaker = spk
                    current_words = [word]
                else:
                    current_words.append(word)
            if current_speaker is not None:
                speaker_blocks.append(f"[ผู้พูดที่ {current_speaker}]: {''.join(current_words).strip()}")
            
            stt_text = "\n".join(speaker_blocks)
            stt_text += "\n\n(System Note: วิเคราะห์บริบทแยกแยะครูกับนักเรียนจากบทสนทนานี้และให้คำตอบที่เหมาะสม)"

        # ── 2. Emotion Detection ──────────────────────────────────────────
        t0 = time.perf_counter()
        try:
            from namo_core.engines.empathy.engine import EmpathyEngine

            if self.emotion_analyzer:
                emotion_result = self.emotion_analyzer.analyze(raw_stt_text)
            else:
                from namo_core.modules.emotion.detector import TextEmotionAnalyzer

                emotion_result = TextEmotionAnalyzer().analyze(raw_stt_text)
            teaching_hint = EmpathyEngine.modifier_from_text_emotion(
                emotion_result["emotion"]
            )
        except Exception as exc:
            logger.warning("Emotion failed: %s", exc)
            emotion_result = {"emotion": "neutral", "confidence": 0.5}
            teaching_hint = ""
        timings["emotion_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        # ── 3. RAG + Reasoning ────────────────────────────────────────────
        t0 = time.perf_counter()
        try:
            if self.reasoner:
                reason = self.reasoner.chat(
                    messages=[{"role": "user", "content": stt_text}],
                    teaching_hint=teaching_hint,
                    session_id=session_id,
                )
            else:
                from namo_core.api.routes.reasoning import get_reasoner

                reason = get_reasoner().chat(
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
            from namo_core.modules.tts.providers.edge_tts_provider import (
                EdgeTTSProvider,
            )

            tts_result = EdgeTTSProvider(default_voice=voice).synthesize(
                answer, voice=voice
            )
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


def run_full_loop(
    *,
    text: str | None = None,
    audio_path: str | None = None,
    session_id: str = "default",
    voice: str = "th-TH-PremwadeeNeural",
    stt_model: str = "tiny",
    language: str = "th",
) -> dict:
    """รัน Full Pipeline: (Audio|Text) → STT → Emotion → Reasoner → TTS"""
    return orchestrator.run_full_loop(
        text=text,
        audio_path=audio_path,
        session_id=session_id,
        voice=voice,
        stt_model=stt_model,
        language=language,
    )
