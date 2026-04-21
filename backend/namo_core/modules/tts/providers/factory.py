"""Factory for building the active TTS provider from settings."""
from __future__ import annotations

from namo_core.config.settings import Settings
from namo_core.modules.tts.providers.base import BaseTTSProvider
from namo_core.modules.tts.providers.mock_provider import MockTTSProvider


def build_tts_provider(settings: Settings) -> tuple[BaseTTSProvider, dict]:
    """Return ``(provider, metadata)`` based on current settings.

    Falls back to ``MockTTSProvider`` when:
    - ``tts_provider`` is unsupported
    - a live provider dependency is unavailable
    - a live provider config is incomplete
    """
    provider_name = settings.tts_provider.lower()
    metadata: dict = {"configured_provider": provider_name}

    if provider_name == "google-cloud":
        try:
            from namo_core.modules.tts.providers.google_tts_provider import GoogleTTSProvider
            provider = GoogleTTSProvider(default_voice=settings.tts_voice)
        except Exception as exc:
            metadata["active_provider"] = "mock"
            metadata["fallback_reason"] = f"Google TTS failed to init: {exc}"
            return MockTTSProvider(), metadata
        
        metadata["active_provider"] = "google-cloud"
        return provider, metadata

    if provider_name == "edge-tts":
        try:
            from namo_core.modules.tts.providers.edge_tts_provider import EdgeTTSProvider

            provider = EdgeTTSProvider(default_voice=settings.tts_voice)
        except ModuleNotFoundError:
            metadata["active_provider"] = "mock"
            metadata["missing_dependency"] = ["edge-tts"]
            metadata["fallback_reason"] = (
                "Edge-TTS dependency unavailable; using mock provider."
            )
            return MockTTSProvider(), metadata

        metadata["active_provider"] = "edge-tts"
        return provider, metadata

    if provider_name == "openai" and settings.tts_api_key:
        from namo_core.modules.tts.providers.openai_tts_provider import OpenAITTSProvider

        provider = OpenAITTSProvider(
            api_key=settings.tts_api_key,
            base_url=settings.tts_api_base_url or "https://api.openai.com",
        )
        metadata["active_provider"] = "openai"
        return provider, metadata

    # Fallback to mock
    missing = []
    if provider_name == "openai" and not settings.tts_api_key:
        missing.append("tts_api_key")
    metadata["active_provider"] = "mock"
    if missing:
        metadata["missing_configuration"] = missing
    elif provider_name != "mock":
        metadata["fallback_reason"] = (
            f"Unsupported TTS provider '{settings.tts_provider}'; using mock provider."
        )
    return MockTTSProvider(), metadata
