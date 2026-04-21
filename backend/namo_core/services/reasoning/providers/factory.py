from namo_core.config.settings import Settings
from namo_core.services.reasoning.providers.base import BaseReasoningProvider
from namo_core.services.reasoning.providers.mock_provider import MockReasoningProvider
from namo_core.services.reasoning.providers.openai_compatible import (
    OpenAICompatibleReasoningProvider,
)


def _provider_metadata(settings: Settings, provider_name: str) -> dict:
    return {
        "name": provider_name,
        "configured_provider": settings.reasoning_provider,
        "active_provider": provider_name,
        "model": settings.reasoning_model,
        "timeout_seconds": settings.reasoning_timeout_seconds,
    }


def build_reasoning_provider(settings: Settings) -> tuple[BaseReasoningProvider, dict]:
    if settings.reasoning_provider == "openai-compatible":
        missing_configuration = [
            name
            for name, value in {
                "reasoning_api_base_url": settings.reasoning_api_base_url,
                "reasoning_api_key": settings.reasoning_api_key,
            }.items()
            if not value
        ]

        if not missing_configuration:
            provider = OpenAICompatibleReasoningProvider(
                base_url=settings.reasoning_api_base_url,
                api_key=settings.reasoning_api_key,
                model=settings.reasoning_model,
                timeout_seconds=settings.reasoning_timeout_seconds,
                system_prompt=settings.reasoning_system_prompt,
            )
            return provider, _provider_metadata(settings, provider.name)

        provider = MockReasoningProvider()
        metadata = _provider_metadata(settings, provider.name)
        metadata["fallback_reason"] = "Reasoning provider config incomplete; using mock provider."
        metadata["missing_configuration"] = missing_configuration
        return provider, metadata

    if settings.reasoning_provider == "vertex-ai":
        try:
            from namo_core.services.reasoning.providers.vertex_ai_provider import VertexAIReasoningProvider
            provider = VertexAIReasoningProvider(
                model=settings.reasoning_model or "gemini-1.5-pro",
                system_prompt=settings.reasoning_system_prompt,
                timeout_seconds=settings.reasoning_timeout_seconds,
                location="asia-southeast1",  # Hardcoded standard region as agreed
            )
            return provider, _provider_metadata(settings, provider.name)
        except Exception as exc:
            provider = MockReasoningProvider()
            metadata = _provider_metadata(settings, provider.name)
            metadata["fallback_reason"] = f"Vertex AI init failed ({exc}); using mock provider."
            return provider, metadata

    if settings.reasoning_provider == "mock":
        provider = MockReasoningProvider()
        return provider, _provider_metadata(settings, provider.name)

    provider = MockReasoningProvider()
    metadata = _provider_metadata(settings, provider.name)
    metadata["fallback_reason"] = (
        f"Unsupported reasoning provider '{settings.reasoning_provider}'; using mock provider."
    )
    return provider, metadata
