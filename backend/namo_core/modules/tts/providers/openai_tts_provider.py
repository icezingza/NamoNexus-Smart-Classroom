"""OpenAI-compatible TTS provider.

Calls the OpenAI /v1/audio/speech endpoint (or any compatible API)
and returns the audio as a base64-encoded string.

Configuration (via .env):
    NAMO_TTS_PROVIDER=openai
    NAMO_TTS_API_KEY=sk-...
    NAMO_TTS_API_BASE_URL=https://api.openai.com   (optional override)
    NAMO_TTS_VOICE=alloy                            (default voice)
"""
from __future__ import annotations

import base64

import httpx

from namo_core.modules.tts.providers.base import BaseTTSProvider


class OpenAITTSProvider(BaseTTSProvider):
    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "tts-1",
        base_url: str = "https://api.openai.com",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def synthesize(self, text: str, voice: str) -> dict:
        url = f"{self.base_url}/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "input": text,
            "voice": voice,
            "response_format": "mp3",
        }
        try:
            response = httpx.post(
                url, json=body, headers=headers, timeout=self.timeout_seconds
            )
            response.raise_for_status()
            audio_b64 = base64.b64encode(response.content).decode("utf-8")
            return {
                "audio_base64": audio_b64,
                "audio_format": "mp3",
                "voice": voice,
                "chars_synthesized": len(text),
                "provider": self.name,
                "model": self.model,
                "status": "ok",
            }
        except httpx.TimeoutException:
            raise RuntimeError(f"TTS request timed out after {self.timeout_seconds}s")
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"TTS API error {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
