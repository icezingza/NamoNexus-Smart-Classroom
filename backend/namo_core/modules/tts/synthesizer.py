"""SpeechSynthesizer — wraps the active TTS provider with error handling."""
from __future__ import annotations

from namo_core.modules.tts.providers.base import BaseTTSProvider


class SpeechSynthesizer:
    """Text-to-speech service with automatic provider fallback."""

    def __init__(self, provider: BaseTTSProvider | None = None) -> None:
        if provider is None:
            from namo_core.config.settings import get_settings
            from namo_core.modules.tts.providers.factory import build_tts_provider

            settings = get_settings()
            provider, _ = build_tts_provider(settings)
            self._default_voice = settings.tts_voice
        else:
            self._default_voice = "demo-th"
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return self._provider.name

    def speak(self, text: str, voice: str | None = None) -> dict:
        """Synthesize text and return a structured result dict."""
        resolved_voice = voice or self._default_voice
        try:
            return self._provider.synthesize(text=text, voice=resolved_voice)
        except Exception as exc:
            # Any provider failure → mock fallback
            from namo_core.modules.tts.providers.mock_provider import MockTTSProvider

            fallback = MockTTSProvider()
            result = fallback.synthesize(text=text, voice=resolved_voice)
            result["fallback_reason"] = str(exc)
            result["original_provider"] = self._provider.name
            return result
