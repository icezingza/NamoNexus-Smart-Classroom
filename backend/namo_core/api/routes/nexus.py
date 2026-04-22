"""NamoNexus Loop API — Phase 7 Integration: ครบวงจรทุกระบบ.

Endpoints:
    POST /nexus/voice-chat      – Phase 4: Audio → STT → RAG → LLM → TTS
                                   Phase 7: + Emotion + Slide context + Event log
    POST /nexus/text-chat       – Phase 7: Text → Emotion → RAG + Slide → LLM → TTS
    POST /nexus/classroom-loop  – Phase 7: Full classroom interaction loop (alias text-chat)

ไม่มีการแก้ไข Core Architecture (engines/, modules/) — ใช้เพียงการเรียกใช้ผ่าน public interface เท่านั้น
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
import wave
from asyncio import to_thread

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from namo_core.config.settings import get_settings
from namo_core.modules.speech.transcriber import (
    MockSpeechTranscriber,
    WhisperSpeechTranscriber,
)
from namo_core.modules.tts.synthesizer import SpeechSynthesizer
from namo_core.services.integration.classroom_pipeline import get_pipeline
from namo_core.services.knowledge.semantic_cache import query_cache
from namo_core.utils.text_formatter import format_diarization
from namo_core.services.reasoning.reasoner import ReasoningService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nexus", tags=["nexus"])

# ─────────────────────────────────────────────────────────────────────────────
# Audio utilities (route-layer only — ไม่แก้ modules ใดๆ)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# DB Logging Utility (Background Task)
# ─────────────────────────────────────────────────────────────────────────────


def _log_event_bg(
    session_id: str,
    query: str,
    response: str,
    emotion: str,
    latency: float,
    source: str,
):
    """Background task สำหรับบันทึก EventLog ลง Database โดยไม่บล็อก API (Phase 12)"""
    try:
        from namo_core.database.core import SessionLocal
        from namo_core.database.models import EventLog

        db = SessionLocal()
        try:
            log = EventLog(
                session_id=session_id,
                event_type=source,
                content=query,
                response=response,
                emotion_state=emotion,
                latency_ms=latency,
            )
            db.add(log)
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.error("Failed to write EventLog to DB: %s", exc)


def _dispatch_bg_log(
    response: dict,
    query: str,
    session_id: str,
    source: str,
    background_tasks: BackgroundTasks,
    latency: float | None = None,
):
    """Helper สำหรับดึงค่าจาก response ไปลง BackgroundTask (ลด Redundancy)"""
    bg_emotion = (
        response.get("emotion", {}).get("smoothed_state", "unknown")
        if isinstance(response.get("emotion"), dict)
        else "unknown"
    )
    bg_response = (
        response.get("reasoning", {}).get("answer", "")
        if isinstance(response.get("reasoning"), dict)
        else str(response.get("reasoning") or "")
    )
    bg_latency = (
        latency
        if latency is not None
        else response.get("pipeline_meta", {}).get("total_ms", 0.0)
    )

    background_tasks.add_task(
        _log_event_bg,
        session_id=session_id,
        query=query,
        response=bg_response,
        emotion=bg_emotion,
        latency=bg_latency,
        source=source,
    )


def _check_semantic_cache(
    query: str,
    session_id: str,
    speak: bool,
    settings: any,
    input_mode: str,
    background_tasks: BackgroundTasks,
) -> dict | None:
    """ตรวจสอบ Semantic Cache และจัดการ Log กรณี Hit"""
    cached_result, similarity = query_cache.get_cached_response(query)
    if cached_result and similarity >= 0.90:
        logger.info(
            f"[CACHE HIT] Semantic cache hit for query '{query}' with similarity {similarity:.2f}"
        )
        cached_result.setdefault("pipeline_meta", {})
        cached_result["pipeline_meta"]["source"] = "semantic_cache"
        cached_result["pipeline_meta"]["similarity"] = similarity
        cached_result["pipeline_meta"]["tts_requested"] = speak
        cached_result["pipeline_meta"]["tts_enabled"] = settings.enable_tts
        cached_result["pipeline_meta"]["input_mode"] = input_mode

        _dispatch_bg_log(
            cached_result,
            query,
            session_id,
            "semantic_cache",
            background_tasks,
            latency=0.0,
        )
        return cached_result
    return None


_TARGET_SAMPLE_RATE = 16_000  # Whisper expects 16kHz


def _resample_int16(
    samples: "import numpy as np; np.ndarray", src_rate: int, dst_rate: int
):
    """Resample int16 audio array using linear interpolation (numpy only, no scipy needed).

    Args:
        samples: 1-D int16 numpy array of audio samples.
        src_rate: Original sample rate in Hz.
        dst_rate: Target sample rate in Hz.

    Returns:
        1-D int16 numpy array resampled to ``dst_rate``.
    """
    import numpy as np

    if src_rate == dst_rate:
        return samples

    f32 = samples.astype(np.float32) / 32768.0
    n_out = max(1, int(len(f32) * dst_rate / src_rate))
    x_old = np.linspace(0.0, 1.0, len(f32))
    x_new = np.linspace(0.0, 1.0, n_out)
    resampled = np.interp(x_new, x_old, f32)
    return (resampled * 32767.0).clip(-32768, 32767).astype(np.int16)


def _audio_to_pcm16(audio_bytes: bytes) -> tuple[bytes, int]:
    """Decode uploaded audio bytes into PCM16 mono at 16kHz.

    Decoding priority:
    1. stdlib ``wave`` — zero extra deps, works for any PCM WAV.
    2. ``soundfile`` — handles MP3, OGG, FLAC, MP4 etc. (installed alongside whisper).
    3. Raises HTTPException 422 if neither strategy succeeds.

    Resampling to 16kHz is applied automatically when the source rate differs.

    Args:
        audio_bytes: Raw bytes of the uploaded audio file.

    Returns:
        Tuple of ``(pcm16_bytes, sample_rate)`` where ``sample_rate`` is always
        ``_TARGET_SAMPLE_RATE`` (16000) after resampling.

    Raises:
        HTTPException 422: If audio cannot be decoded.
    """
    import numpy as np

    # ── Strategy 1: stdlib wave (PCM WAV) ─────────────────────────────────────
    try:
        with wave.open(io.BytesIO(audio_bytes)) as wf:
            src_rate: int = wf.getframerate()
            n_channels: int = wf.getnchannels()
            raw_pcm: bytes = wf.readframes(wf.getnframes())

            samples = np.frombuffer(raw_pcm, dtype=np.int16).copy()
            if n_channels > 1:
                # Interleaved multi-channel → keep only channel 0 (mono)
                samples = samples[::n_channels]

            samples = _resample_int16(samples, src_rate, _TARGET_SAMPLE_RATE)
            logger.debug(
                "audio decoded via wave: src_rate=%d channels=%d → resampled to %d",
                src_rate,
                n_channels,
                _TARGET_SAMPLE_RATE,
            )
            return samples.tobytes(), _TARGET_SAMPLE_RATE
    except wave.Error:
        pass  # Not a valid WAV — try next strategy
    except Exception as exc:
        logger.warning("wave decode failed unexpectedly: %s", exc)

    # ── Strategy 2: soundfile (installed with whisper / librosa) ──────────────
    try:
        import soundfile as sf

        data, src_rate = sf.read(
            io.BytesIO(audio_bytes), dtype="int16", always_2d=False
        )
        if data.ndim > 1:
            data = data[:, 0]  # Pick first channel → mono

        data = _resample_int16(data, src_rate, _TARGET_SAMPLE_RATE)
        logger.debug(
            "audio decoded via soundfile: src_rate=%d → resampled to %d",
            src_rate,
            _TARGET_SAMPLE_RATE,
        )
        return data.tobytes(), _TARGET_SAMPLE_RATE
    except ImportError:
        logger.debug("soundfile not installed — only WAV files are supported")
    except Exception as exc:
        logger.warning("soundfile decode failed: %s", exc)

    # ── No strategy succeeded ─────────────────────────────────────────────────
    raise HTTPException(
        status_code=422,
        detail=(
            "ไม่สามารถถอดรหัสไฟล์เสียงได้ (Cannot decode audio file). "
            "กรุณาอัปโหลดไฟล์ WAV (PCM16, 16kHz, mono) "
            "หรือติดตั้ง soundfile เพื่อรองรับรูปแบบอื่น (MP3, OGG, FLAC): "
            "`pip install soundfile`"
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/voice-chat")
async def voice_chat(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(
        ...,
        description="ไฟล์เสียง (WAV PCM16 16kHz แนะนำ; รองรับ MP3/OGG หาก soundfile ติดตั้งอยู่)",
    ),
    voice: str | None = Query(
        default=None,
        description="ชื่อ TTS voice เพื่อ override ค่าเริ่มต้น เช่น 'th-TH-PremwadeeNeural'",
    ),
    speak: bool = Query(
        default=True,
        description="หาก True จะสังเคราะห์เสียงตอบกลับด้วย TTS (Edge-TTS)",
    ),
    session_id: str = Query(
        default="DEMO_SESSION_001",
        description="Session ID สำหรับบันทึก EventLog",
    ),
) -> dict:
    """NamoNexus Loop — pipeline เสียงครบวงจร (Phase 4).

    รับไฟล์เสียงจากผู้ใช้ และรันผ่านทุกระบบของ NamoNexus:

    1. **STT** — Whisper ถอดเสียงเป็นข้อความ
    2. **RAG** — FAISS ค้นหาบริบทธรรมะที่เกี่ยวข้อง
    3. **LLM** — Reasoning service สร้างคำตอบจากบริบท
    4. **TTS** — Edge-TTS แปลงคำตอบกลับเป็นเสียง (เมื่อ speak=True)

    Args:
        audio: ไฟล์เสียงที่อัปโหลด (WAV แนะนำ, หรือ MP3/OGG/FLAC หาก soundfile ติดตั้ง)
        voice: ชื่อ TTS voice (optional, override ค่าจาก settings)
        speak: หาก True จะ synthesize เสียงตอบกลับ

    Returns:
        JSON dict ประกอบด้วย:
        - ``transcript`` — ผลการถอดเสียง (text, confidence, language, provider)
        - ``reasoning``  — คำตอบจาก LLM พร้อม sources จาก FAISS
        - ``tts``        — ผลการสังเคราะห์เสียง (audio_base64 เมื่อ speak=True)
        - ``pipeline_meta`` — ข้อมูล metadata ของ pipeline

    Raises:
        HTTPException 400: ไม่สามารถอ่านไฟล์เสียงได้
        HTTPException 422: ไฟล์เสียงว่างเปล่าหรือถอดรหัสไม่ได้
        HTTPException 503: บริการ STT/LLM/TTS ไม่พร้อมใช้งาน
    """
    settings = get_settings()

    # ── Step 1: Read uploaded audio bytes ─────────────────────────────────────
    try:
        audio_bytes = await audio.read()
    except Exception as exc:
        logger.error("Failed to read uploaded audio file '%s': %s", audio.filename, exc)
        raise HTTPException(
            status_code=400,
            detail=f"ไม่สามารถอ่านไฟล์เสียงได้: {exc}",
        ) from exc

    if not audio_bytes:
        raise HTTPException(
            status_code=422, detail="ไฟล์เสียงที่อัปโหลดว่างเปล่า (empty file)"
        )

    logger.info(
        "voice-chat request: file='%s' size=%d bytes speak=%s",
        audio.filename,
        len(audio_bytes),
        speak,
    )

    # ── Step 2: Decode audio → PCM16 16kHz mono ───────────────────────────────
    try:
        pcm16_bytes, sample_rate = _audio_to_pcm16(audio_bytes)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected audio decode error: %s", exc)
        raise HTTPException(
            status_code=422, detail=f"Audio decode error: {exc}"
        ) from exc

    # ── Step 3: Speech-to-Text (Whisper หรือ Mock) ────────────────────────────
    provider_name = settings.speech_provider.lower()
    try:
        if provider_name in {"whisper-local", "whisper", "real"}:
            transcriber = WhisperSpeechTranscriber(
                model_name=settings.speech_model,
                language=settings.speech_language,
            )
        else:
            logger.debug("Using MockSpeechTranscriber (provider='%s')", provider_name)
            transcriber = MockSpeechTranscriber()

        transcript_result = await to_thread(
            transcriber.transcribe_pcm16,
            pcm16_bytes,
            sample_rate,
        )
        logger.info(
            "STT result: provider=%s text='%.80s' confidence=%.2f",
            transcriber.name,
            transcript_result.get("text", ""),
            transcript_result.get("confidence", 0.0),
        )
    except Exception as exc:
        logger.error("STT failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Speech-to-text ล้มเหลว: {exc}",
        ) from exc

    query_text: str = transcript_result.get("text", "").strip()
    raw_text: str = query_text

    # หากไม่พบเสียงพูด → คืนค่าผลลัพธ์ partial (ไม่ error)
    if not raw_text:
        logger.info(
            "STT returned empty text (no speech detected) for file '%s'", audio.filename
        )
        return {
            "transcript": {
                "text": "",
                "confidence": transcript_result.get("confidence", 0.0),
                "language": transcript_result.get("language", settings.speech_language),
                "status": "no-match",
                "provider": transcriber.name,
            },
            "reasoning": None,
            "tts": None,
            "pipeline_meta": {
                "audio_filename": audio.filename,
                "sample_rate": sample_rate,
                "step_completed": "stt",
                "note": "ไม่พบเสียงพูดในไฟล์เสียง — กรุณาลองอีกครั้ง",
            },
        }

    # ── Phase 12: Apply Speaker Diarization formatting for LLM ────────────────
    if diarization_data := transcript_result.get("diarization", []):
        if formatted_text := format_diarization(diarization_data):
            query_text = formatted_text
            logger.info("Diarization applied. Formatted query:\n%s", query_text)

    # ── Phase 14: Semantic Cache Check สำหรับเสียง ────────────────────────────
    if cache_hit := _check_semantic_cache(
        query_text, session_id, speak, settings, "voice", background_tasks
    ):
        cache_hit["transcript"] = {
            "text": query_text,
            "confidence": transcript_result.get("confidence", 0.0),
            "language": transcript_result.get("language", settings.speech_language),
            "status": "ok",
            "provider": transcriber.name,
        }
        return cache_hit

    # ── Step 4–6: ClassroomPipeline (Emotion + Slide context + RAG + LLM + TTS) ──
    # Phase 7 Integration: delegate to ClassroomPipeline for unified processing
    try:
        pipeline_result = await get_pipeline().run(
            query=query_text,
            transcript={
                "text": raw_text,
                "confidence": transcript_result.get("confidence", 0.0),
                "diarization": diarization,
            },
            speak=speak and settings.enable_tts,
            voice=voice,
        )
        logger.info(
            "Pipeline done: stages=%s emotion=%s",
            pipeline_result["pipeline_meta"]["stages_completed"],
            pipeline_result.get("emotion", {}).get("smoothed_state", "n/a"),
        )
    except Exception as exc:
        logger.error("ClassroomPipeline failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Pipeline ล้มเหลว: {exc}",
        ) from exc

    # ── Compose final response ────────────────────────────────────────────────
    response = {
        "transcript": {
            "text": query_text,
            "confidence": transcript_result.get("confidence", 0.0),
            "language": transcript_result.get("language", settings.speech_language),
            "status": "ok",
            "provider": transcriber.name,
        },
        "reasoning": pipeline_result.get("reasoning"),
        "emotion": pipeline_result.get("emotion"),
        "teaching_hint": pipeline_result.get("teaching_hint", ""),
        "tone": pipeline_result.get("tone", "calm"),
        "student_state": pipeline_result.get("student_state", "attentive"),
        "slide_context": pipeline_result.get("slide_context"),
        "tts": pipeline_result.get("tts"),
        "pipeline_meta": {
            **pipeline_result.get("pipeline_meta", {}),
            "audio_filename": audio.filename,
            "audio_size_bytes": len(audio_bytes),
            "sample_rate": sample_rate,
            "tts_requested": speak,
            "tts_enabled": settings.enable_tts,
        },
    }

    query_cache.add_to_cache(query_text, response)

    _dispatch_bg_log(
        response, query_text, session_id, "voice_pipeline", background_tasks
    )

    return response


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7: Text-based endpoints (no audio required)
# ─────────────────────────────────────────────────────────────────────────────


class TextChatRequest(BaseModel):
    """Request body for text-based classroom interaction."""

    text: str = Field(
        min_length=1, max_length=1000, description="Student question or input text"
    )
    attention_score: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Optional vision attention signal [0.0–1.0]",
    )
    session_id: str = Field(
        default="DEMO_SESSION_001",
        description="Session ID สำหรับบันทึก EventLog",
    )


@router.post("/text-chat")
async def text_chat(
    payload: TextChatRequest,
    background_tasks: BackgroundTasks,
    speak: bool = Query(default=False, description="Synthesise TTS response"),
    voice: str | None = Query(default=None, description="TTS voice override"),
) -> dict:
    """Phase 7 — Full classroom pipeline for text input (no audio needed).

    Runs the complete integration loop:
    Text → Emotion (attention + speech energy) → Slide context
         → Knowledge RAG → LLM (with teaching_hint) → TTS (optional)
         → Event log

    Useful for:
    - Dashboard chat interface
    - Testing the pipeline without audio hardware
    - Automated integration tests

    Args:
        payload: text input + optional attention_score from webcam
        speak: If True, synthesise TTS audio for the answer
        voice: Optional TTS voice override

    Returns:
        Full pipeline result dict identical in shape to /nexus/voice-chat
    """
    settings = get_settings()
    query = payload.text.strip()

    # Phase 14: Semantic Cache Check
    if cache_hit := _check_semantic_cache(
        query, payload.session_id, speak, settings, "text", background_tasks
    ):
        return cache_hit

    result = await get_pipeline().run(
        query=query,
        transcript={"text": query, "confidence": 0.85},
        perception={"attention_score": payload.attention_score, "engagement": "active"},
        speak=speak and settings.enable_tts,
        voice=voice,
    )

    # Construct the full response and cache it
    response = {
        "query": result["query"],
        "reasoning": result.get("reasoning"),
        "emotion": result.get("emotion"),
        "teaching_hint": result.get("teaching_hint", ""),
        "tone": result.get("tone", "calm"),
        "student_state": result.get("student_state", "attentive"),
        "slide_context": result.get("slide_context"),
        "tts": result.get("tts"),
        "pipeline_meta": {
            **result.get("pipeline_meta", {}),
            "input_mode": "text",
            "tts_requested": speak,
            "tts_enabled": settings.enable_tts,
        },
    }
    query_cache.add_to_cache(query, response)

    bg_emotion = (
        response.get("emotion", {}).get("smoothed_state", "unknown")
        if isinstance(response.get("emotion"), dict)
        else "unknown"
    )
    bg_response = (
        response.get("reasoning", {}).get("answer", "")
        if isinstance(response.get("reasoning"), dict)
        else str(response.get("reasoning") or "")
    )
    bg_latency = response.get("pipeline_meta", {}).get("total_ms", 0.0)
    background_tasks.add_task(
        _log_event_bg,
        session_id=payload.session_id,
        query=query,
        response=bg_response,
        emotion=bg_emotion,
        latency=bg_latency,
        source="text_pipeline",
    )

    return response


@router.post("/classroom-loop")
async def classroom_loop(
    payload: TextChatRequest,
    background_tasks: BackgroundTasks,
    speak: bool = Query(default=True, description="Synthesise TTS response"),
    voice: str | None = Query(default=None, description="TTS voice override"),
) -> dict:
    """Phase 7 — Alias for /nexus/text-chat with speak=True default.

    Named 'classroom-loop' to match the system architecture terminology.
    Intended as the primary endpoint called during a live classroom session.

    The loop:
        Student Input → Emotion Detect → Slide Context
            → Knowledge RAG → LLM (teaching_hint) → TTS
            → Classroom Event Log → State Transition

    Returns the same shape as /nexus/text-chat.
    """
    settings = get_settings()
    query = payload.text.strip()

    # Phase 14: Semantic Cache Check
    if cache_hit := _check_semantic_cache(
        query, payload.session_id, speak, settings, "classroom-loop", background_tasks
    ):
        return cache_hit

    result = await get_pipeline().run(
        query=query,
        transcript={"text": query, "confidence": 0.85},
        perception={"attention_score": payload.attention_score, "engagement": "active"},
        speak=speak and settings.enable_tts,
        voice=voice,
    )

    # Construct the full response and cache it
    response = {
        "query": result["query"],
        "reasoning": result.get("reasoning"),
        "emotion": result.get("emotion"),
        "teaching_hint": result.get("teaching_hint", ""),
        "tone": result.get("tone", "calm"),
        "student_state": result.get("student_state", "attentive"),
        "slide_context": result.get("slide_context"),
        "tts": result.get("tts"),
        "pipeline_meta": {
            **result.get("pipeline_meta", {}),
            "input_mode": "classroom-loop",
            "tts_requested": speak,
            "tts_enabled": settings.enable_tts,
        },
    }
    query_cache.add_to_cache(query, response)

    bg_emotion = (
        response.get("emotion", {}).get("smoothed_state", "unknown")
        if isinstance(response.get("emotion"), dict)
        else "unknown"
    )
    bg_response = (
        response.get("reasoning", {}).get("answer", "")
        if isinstance(response.get("reasoning"), dict)
        else str(response.get("reasoning") or "")
    )
    bg_latency = response.get("pipeline_meta", {}).get("total_ms", 0.0)
    background_tasks.add_task(
        _log_event_bg,
        session_id=payload.session_id,
        query=query,
        response=bg_response,
        emotion=bg_emotion,
        latency=bg_latency,
        source="classroom_loop",
    )

    return response
