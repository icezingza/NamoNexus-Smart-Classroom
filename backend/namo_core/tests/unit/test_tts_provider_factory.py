import base64
import importlib
import types

import pytest

from namo_core.config.settings import Settings
from namo_core.modules.tts.providers.factory import build_tts_provider


def test_edge_tts_provider_encodes_audio_chunks(monkeypatch) -> None:
    provider_module = importlib.import_module(
        "namo_core.modules.tts.providers.edge_tts_provider"
    )
    captured: dict = {}

    class DummyCommunicate:
        def __init__(self, text: str, voice: str) -> None:
            captured["text"] = text
            captured["voice"] = voice

        async def stream(self):
            yield {"type": "audio", "data": b"na"}
            yield {"type": "metadata", "data": b"ignored"}
            yield {"type": "audio", "data": b"mo"}

    monkeypatch.setattr(
        provider_module.importlib,
        "import_module",
        lambda name: types.SimpleNamespace(Communicate=DummyCommunicate),
    )

    provider = provider_module.EdgeTTSProvider(default_voice="demo-th")
    payload = provider.synthesize(text="Namo", voice="demo-th")

    assert payload["audio_base64"] == base64.b64encode(b"namo").decode("utf-8")
    assert payload["audio_format"] == "mp3"
    assert payload["voice"] == "th-TH-NiwatNeural"
    assert payload["chars_synthesized"] == 4
    assert payload["provider"] == "edge-tts"
    assert payload["status"] == "ok"
    assert captured["text"] == "Namo"
    assert captured["voice"] == "th-TH-NiwatNeural"


def test_edge_tts_provider_raises_runtime_error_on_stream_failure(monkeypatch) -> None:
    provider_module = importlib.import_module(
        "namo_core.modules.tts.providers.edge_tts_provider"
    )

    class FailingCommunicate:
        def __init__(self, text: str, voice: str) -> None:
            self.text = text
            self.voice = voice

        async def stream(self):
            if False:
                yield {"type": "audio", "data": b""}
            raise RuntimeError("network down")

    monkeypatch.setattr(
        provider_module.importlib,
        "import_module",
        lambda name: types.SimpleNamespace(Communicate=FailingCommunicate),
    )

    provider = provider_module.EdgeTTSProvider()

    with pytest.raises(RuntimeError, match="Edge-TTS synthesis failed: network down"):
        provider.synthesize(text="Hello", voice="en-US-AriaNeural")


def test_tts_provider_factory_selects_edge_tts(monkeypatch) -> None:
    provider_module = importlib.import_module(
        "namo_core.modules.tts.providers.edge_tts_provider"
    )

    class DummyCommunicate:
        def __init__(self, text: str, voice: str) -> None:
            self.text = text
            self.voice = voice

        async def stream(self):
            if False:
                yield {"type": "audio", "data": b""}
            return

    monkeypatch.setattr(
        provider_module.importlib,
        "import_module",
        lambda name: types.SimpleNamespace(Communicate=DummyCommunicate),
    )

    provider, metadata = build_tts_provider(Settings(tts_provider="edge-tts"))

    assert provider.name == "edge-tts"
    assert metadata["configured_provider"] == "edge-tts"
    assert metadata["active_provider"] == "edge-tts"


def test_tts_provider_factory_falls_back_when_edge_tts_dependency_missing(
    monkeypatch,
) -> None:
    provider_module = importlib.import_module(
        "namo_core.modules.tts.providers.edge_tts_provider"
    )

    def fail_import(name: str):
        raise ModuleNotFoundError("No module named 'edge_tts'")

    monkeypatch.setattr(provider_module.importlib, "import_module", fail_import)

    provider, metadata = build_tts_provider(Settings(tts_provider="edge-tts"))

    assert provider.name == "mock"
    assert metadata["configured_provider"] == "edge-tts"
    assert metadata["active_provider"] == "mock"
    assert metadata["missing_dependency"] == ["edge-tts"]
    assert metadata["fallback_reason"] == "Edge-TTS dependency unavailable; using mock provider."
