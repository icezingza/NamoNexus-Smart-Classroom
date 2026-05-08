"""Speech API routes — GET /speech/status, POST /speech/transcribe.

Exposes the SpeechRecognizer (Whisper-local or mock) over HTTP.
The transcribe endpoint runs a single listen-and-transcribe cycle using the
Voice Activity Detector (VAD) + StreamingAudioBuffer already wired up in
:class:`~namo_core.modules.speech.recognizer.SpeechRecognizer`.

Typical response (real provider):
    {
        "text": "อริยสัจ 4 คืออะไร",
        "confidence": 0.87,
        "status": "ok",          # ok | idle | no-match | unavailable | mock
        "provider": "whisper-local",
        "language": "th",
        "vad": { ... },
        "audio": { "duration_ms": 1800, ... }
    }
"""
from __future__ import annotations

import logging
import os
import tempfile

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from namo_core.modules.speech.recognizer import SpeechRecognizer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/speech", tags=["speech"])

# Max audio upload: 25 MB — typical webm/mp3 under 8s is well under 1 MB
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


@router.get("/status")
def speech_status() -> dict:
    """Return the active speech provider and microphone readiness."""
    recognizer = SpeechRecognizer()
    from namo_core.devices.microphone.capture import (
        MicrophoneCaptureConfig,
        probe_microphone_status,
    )
    from namo_core.config.settings import get_settings

    settings = get_settings()
    device_status = probe_microphone_status(
        MicrophoneCaptureConfig(
            sample_rate=settings.speech_sample_rate,
            channels=settings.speech_channels,
            chunk_ms=settings.speech_chunk_ms,
        )
    )
    return {
        "provider": recognizer.provider_name,
        "model": settings.speech_model,
        "language": settings.speech_language,
        "enabled": True,
        "device": device_status,
    }


@router.post("/transcribe")
def transcribe() -> dict:
    """Run one listen-and-transcribe cycle and return the result."""
    try:
        recognizer = SpeechRecognizer()
        result = recognizer.transcribe()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if result.get("status") == "error":
        raise HTTPException(
            status_code=503,
            detail=result.get("error", "Speech transcription error"),
        )

    return result


@router.post("/transcribe-upload")
async def transcribe_upload(audio: UploadFile = File(...)) -> dict:
    """รับไฟล์เสียงจาก Browser แล้วแปลงเป็นข้อความด้วย FasterWhisper."""
    from namo_core.config.settings import get_settings
    settings = get_settings()

    raw_bytes = await audio.read(_MAX_UPLOAD_BYTES + 1)
    if len(raw_bytes) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Audio file too large. Maximum size is 25 MB.",
        )

    tmp_path: str | None = None
    try:
        from namo_core.modules.speech.transcriber import FasterWhisperTranscriber

        suffix = os.path.splitext(audio.filename or "audio.webm")[1] or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name

        transcriber = FasterWhisperTranscriber(
            model_name=settings.speech_model,
            language=settings.speech_language,
        )
        result = transcriber.transcribe_file(tmp_path)
    except HTTPException:
        raise
    except (ValueError, RuntimeError) as exc:
        logger.error("Transcription failed (known error): %s", exc, exc_info=True)
        detail = str(exc) if settings.env != "production" else "Transcription service unavailable"
        raise HTTPException(status_code=503, detail=detail) from exc
    except Exception as exc:
        logger.error("Transcription failed (unexpected): %s", exc, exc_info=True)
        detail = str(exc) if settings.env != "production" else "Transcription service unavailable"
        raise HTTPException(status_code=503, detail=detail) from exc
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError as cleanup_exc:
                logger.warning("Failed to remove temp file %s: %s", tmp_path, cleanup_exc)

    return {
        "transcript": result.get("text", ""),
        "confidence": result.get("confidence", 0.0),
        "language":   result.get("language", "th"),
        "provider":   "faster-whisper",
        "status":     "ok" if result.get("text") else "no-match",
    }
