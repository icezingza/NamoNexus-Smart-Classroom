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

import tempfile, os
from fastapi import APIRouter, File, HTTPException, UploadFile

from namo_core.modules.speech.recognizer import SpeechRecognizer

router = APIRouter(prefix="/speech", tags=["speech"])


@router.get("/status")
def speech_status() -> dict:
    """Return the active speech provider and microphone readiness.

    Returns:
        Dict with ``provider``, ``enabled``, and ``device`` sub-dict.
    """
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
    """Run one listen-and-transcribe cycle and return the result.

    Uses VAD to detect speech start/end automatically. Returns immediately
    with ``status: idle`` if no speech is detected within the listen timeout.

    Raises:
        HTTPException 503: When the microphone or Whisper model is unavailable.
    """
    try:
        recognizer = SpeechRecognizer()
        result = recognizer.transcribe()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Surface errors as 503 so the client can retry cleanly
    if result.get("status") == "error":
        raise HTTPException(
            status_code=503,
            detail=result.get("error", "Speech transcription error"),
        )

    return result


@router.post("/transcribe-upload")
async def transcribe_upload(audio: UploadFile = File(...)) -> dict:
    """รับไฟล์เสียงจาก Browser (webm/wav/mp3) แล้วแปลงเป็นข้อความด้วย FasterWhisper.

    ใช้สำหรับ Push-to-Talk จาก Tablet ที่ส่ง MediaRecorder blob มาผ่าน HTTP.

    Returns:
        Dict with ``transcript``, ``confidence``, ``language``, ``provider``.
    """
    try:
        from namo_core.modules.speech.transcriber import FasterWhisperTranscriber
        from namo_core.config.settings import get_settings
        settings = get_settings()

        # บันทึกไฟล์ลง temp
        suffix = os.path.splitext(audio.filename or "audio.webm")[1] or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await audio.read())
            tmp_path = tmp.name

        transcriber = FasterWhisperTranscriber(
            model_name=settings.speech_model,
            language=settings.speech_language,
        )
        result = transcriber.transcribe_file(tmp_path)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        try: os.unlink(tmp_path)
        except Exception: pass

    return {
        "transcript": result.get("text", ""),
        "confidence": result.get("confidence", 0.0),
        "language":   result.get("language", "th"),
        "provider":   "faster-whisper",
        "status":     "ok" if result.get("text") else "no-match",
    }
