import asyncio
import httpx

import namo_core.services.reasoning.reasoner as reasoner_module
from namo_core.services.reasoning.providers.base import BaseReasoningProvider
from namo_core.services.reasoning.providers.factory import build_reasoning_provider
from namo_core.services.reasoning.providers.openai_compatible import (
    OpenAICompatibleReasoningProvider,
)
from namo_core.services.reasoning.reasoner import ReasoningService
from namo_core.config.settings import Settings


def test_reasoning_service_exposes_provider_metadata(monkeypatch) -> None:
    import namo_core.config.settings as _s
    monkeypatch.setattr(_s, "_settings_instance", None)
    monkeypatch.setenv("NAMO_REASONING_PROVIDER", "mock")
    monkeypatch.setenv("NAMO_REASONING_ALLOW_MOCK_FALLBACK", "true")
    payload = asyncio.run(ReasoningService().explain("mindfulness"))
    assert payload["provider"] == "mock"
    assert payload["provider_metadata"]["name"] == "mock"
    assert payload["provider_metadata"]["active_provider"] == "mock"


def test_reasoning_provider_factory_falls_back_for_incomplete_config() -> None:
    settings = Settings(
        reasoning_provider="openai-compatible",
        reasoning_api_base_url="http://localhost:8001/v1",
        reasoning_api_key=None,
    )

    provider, metadata = build_reasoning_provider(settings)

    assert provider.name == "mock"
    assert metadata["configured_provider"] == "openai-compatible"
    assert metadata["missing_configuration"] == ["reasoning_api_key"]


def test_openai_compatible_provider_handles_structured_content(monkeypatch) -> None:
    provider = OpenAICompatibleReasoningProvider(
        base_url="http://localhost:8001/v1",
        api_key="test-key",
        model="demo-model",
        timeout_seconds=12.5,
        system_prompt="Teaching system prompt.",
    )

    # Mock _request_completion — avoids httpx network call, tests generate() orchestration
    async def fake_request_completion(messages: list[dict]) -> str:
        assert messages[0]["content"] == "Teaching system prompt."
        assert messages[0]["role"] == "system"
        return "Mindfulness starts with breathing.\nReturn attention gently."

    monkeypatch.setattr(provider, "_request_completion", fake_request_completion)

    payload = asyncio.run(provider.generate(query="Explain mindfulness.", context="Breathing awareness."))

    assert payload["provider"] == "openai-compatible"
    assert payload["answer"] == "Mindfulness starts with breathing.\nReturn attention gently."
    assert payload["model"] == "demo-model"


def test_reasoning_service_falls_back_when_runtime_provider_fails(monkeypatch) -> None:
    import namo_core.config.settings as _s
    monkeypatch.setattr(_s, "_settings_instance", None)
    monkeypatch.setenv("NAMO_REASONING_ALLOW_MOCK_FALLBACK", "true")

    class FailingProvider(BaseReasoningProvider):
        name = "openai-compatible"

        async def generate(self, query: str, context: str) -> dict:
            raise httpx.TimeoutException("provider timeout")

        async def chat(self, messages: list[dict], context: str) -> dict:
            raise httpx.TimeoutException("provider timeout")

    def fake_build_reasoning_provider(settings: Settings) -> tuple[BaseReasoningProvider, dict]:
        return (
            FailingProvider(),
            {
                "name": "openai-compatible",
                "configured_provider": "openai-compatible",
                "active_provider": "openai-compatible",
                "model": settings.reasoning_model,
                "timeout_seconds": settings.reasoning_timeout_seconds,
            },
        )

    monkeypatch.setattr(reasoner_module, "build_reasoning_provider", fake_build_reasoning_provider)

    payload = asyncio.run(ReasoningService().explain("mindfulness"))

    assert payload["provider"] == "mock"
    assert payload["provider_metadata"]["name"] == "mock"
    assert payload["provider_metadata"]["active_provider"] == "mock"
    assert payload["provider_metadata"]["attempted_provider"] == "openai-compatible"
    assert payload["provider_metadata"]["provider_error"] == "TimeoutException"
