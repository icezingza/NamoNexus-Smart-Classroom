"""Base interface for TTS providers."""
from __future__ import annotations


class BaseTTSProvider:
    name: str = "base"

    def synthesize(self, text: str, voice: str) -> dict:
        """Synthesize text to speech.

        Returns a dict with at minimum:
          - audio_base64: str | None  (None when no audio bytes produced)
          - voice: str
          - chars_synthesized: int
          - provider: str
        """
        raise NotImplementedError
