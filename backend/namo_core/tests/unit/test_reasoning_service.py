import httpx

import namo_core.services.reasoning.reasoner as reasoner_module
from namo_core.services.reasoning.providers.base import BaseReasoningProvider
from namo_core.services.reasoning.providers.factory import build_reasoning_provider
from namo_core.services.reasoning.providers.openai_compatible import (
    OpenAICompatibleReasoningProvider,
)
from namo_core.services.reasoning.reasoner import ReasoningService
from namo_core.config.settings import Settings


def test_reasoning_service_exposes_provider_metadata() -> None:
    payload = ReasoningService().explain("mindfulness")
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
    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "text", "text": "Mindfulness starts with breathing."},
                                {"type": "text", "text": "Return attention gently."},
                            ]
                        }
                    }
                ]
            }

    captured: dict = {}

    def fake_post(url: str, headers: dict, json: dict, timeout: float) -> DummyResponse:
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr(
        "namo_core.services.reasoning.providers.openai_compatible.httpx.post",
        fake_post,
    )

    provider = OpenAICompatibleReasoningProvider(
        base_url="http://localhost:8001/v1",
        api_key="test-key",
        model="demo-model",
        timeout_seconds=12.5,
        system_prompt="Teaching system prompt.",
    )

    payload = provider.generate(query="Explain mindfulness.", context="Breathing awareness.")

    assert payload["provider"] == "openai-compatible"
    assert payload["answer"] == "Mindfulness starts with breathing.\nReturn attention gently."
    assert captured["timeout"] == 12.5
    assert captured["json"]["messages"][0]["content"] == "Teaching system prompt."


def test_reasoning_service_falls_back_when_runtime_provider_fails(monkeypatch) -> None:
    class FailingProvider(BaseReasoningProvider):
        name = "openai-compatible"

        def generate(self, query: str, context: str) -> dict:
            raise httpx.TimeoutException("provider timeout")

        def chat(self, messages: list[dict], context: str) -> dict:
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

    payload = ReasoningService().explain("mindfulness")

    assert payload["provider"] == "mock"
    assert payload["provider_metadata"]["name"] == "mock"
    assert payload["provider_metadata"]["active_provider"] == "mock"
    assert payload["provider_metadata"]["attempted_provider"] == "openai-compatible"
    assert payload["provider_metadata"]["provider_error"] == "TimeoutException"
