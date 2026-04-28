"""TTS API routes — POST /tts/speak, POST /tts/generate, GET /tts/status."""
from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from namo_core.modules.tts.synthesizer import SpeechSynthesizer

router = APIRouter(prefix="/tts", tags=["tts"])

# เสียงหลักของนะโม — Premwadee (หญิง) ตาม Phase 3 spec
NAMO_DEFAULT_VOICE = "th-TH-PremwadeeNeural"


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    voice: str | None = None


class GenerateRequest(BaseModel):
    """Request body สำหรับ /tts/generate — คืนไฟล์ MP3 โดยตรง"""

    text: str = Field(
        min_length=1,
        max_length=2000,
        description="ข้อความที่ต้องการให้พูด",
    )
    voice: str = Field(
        default=NAMO_DEFAULT_VOICE,
        description="Edge-TTS voice name เช่น th-TH-PremwadeeNeural",
    )


import asyncio

@router.post("/speak")
async def speak(payload: SpeakRequest) -> dict:
    """Synthesize text to speech — คืน JSON พร้อม audio_base64

    Returns structured metadata. `audio_base64` is non-null only when
    a real TTS provider (e.g. edge-tts) is configured via NAMO_TTS_PROVIDER.
    When using the mock provider, `audio_base64` is null and `status` is "mock".
    """
    try:
        synthesizer = SpeechSynthesizer()
        return await asyncio.to_thread(synthesizer.speak, text=payload.text, voice=payload.voice)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/generate",
    response_class=Response,
    responses={
        200: {
            "content": {"audio/mpeg": {}},
            "description": "MP3 audio stream ของข้อความที่ส่งมา",
        }
    },
)
async def generate(payload: GenerateRequest) -> Response:
    """สร้างไฟล์เสียง MP3 จากข้อความ — คืน raw binary ให้ client เล่นได้ทันที

    ใช้เสียง th-TH-PremwadeeNeural (นะโม) เป็น default
    ต้องตั้งค่า NAMO_TTS_PROVIDER=edge-tts ใน .env

    Example::

        curl -X POST /api/tts/generate \\
             -H "Content-Type: application/json" \\
             -d '{"text": "สวัสดีค่ะ"}' \\
             --output namo.mp3
    """
    try:
        synthesizer = SpeechSynthesizer()
        result = await asyncio.to_thread(synthesizer.speak, text=payload.text, voice=payload.voice)

        if result.get("status") == "mock" or not result.get("audio_base64"):
            raise HTTPException(
                status_code=503,
                detail=(
                    "TTS provider is in mock mode — no audio generated. "
                    "Set NAMO_TTS_PROVIDER=edge-tts in .env to enable real synthesis."
                ),
            )

        audio_bytes = base64.b64decode(result["audio_base64"])
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=namo_tts.mp3",
                "X-Voice": result.get("voice", payload.voice),
                "X-Chars-Synthesized": str(result.get("chars_synthesized", 0)),
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/status")
def tts_status() -> dict:
    """Return the active TTS provider name, default voice and readiness."""
    synthesizer = SpeechSynthesizer()
    return {
        "provider":      synthesizer.provider_name,
        "default_voice": NAMO_DEFAULT_VOICE,
        "enabled":       True,
        "ready":         synthesizer.provider_name != "mock",
    }
