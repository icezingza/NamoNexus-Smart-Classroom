"""Mock TTS provider — returns structured metadata without producing audio.

Safe for offline/test environments. No external dependencies required.
"""
from __future__ import annotations

from namo_core.modules.tts.providers.base import BaseTTSProvider


class MockTTSProvider(BaseTTSProvider):
    name = "mock"

    def synthesize(self, text: str, voice: str) -> dict:
        return {
            "audio_base64": None,
            "voice": voice,
            "chars_synthesized": len(text),
            "provider": self.name,
            "status": "mock",
            "note": "Configure NAMO_TTS_PROVIDER=edge-tts or openai for real audio synthesis.",
        }
