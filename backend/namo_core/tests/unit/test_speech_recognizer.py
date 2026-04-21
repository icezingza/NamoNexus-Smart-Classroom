from __future__ import annotations

import numpy as np

from namo_core.config.settings import Settings
from namo_core.devices.microphone.capture import MicrophoneCaptureConfig
from namo_core.modules.speech.recognizer import SpeechRecognizer
from namo_core.modules.speech.streaming_buffer import StreamingAudioBuffer
from namo_core.modules.speech.vad import EnergyVoiceActivityDetector


def _pcm_chunk(level: int, samples: int = 480) -> bytes:
    return np.full(samples, level, dtype=np.int16).tobytes()


class FakeTranscriber:
    name = "whisper-local"

    def __init__(self) -> None:
        self.calls: list[tuple[bytes, int]] = []

    def transcribe_pcm16(self, audio_bytes: bytes, sample_rate: int) -> dict:
        self.calls.append((audio_bytes, sample_rate))
        return {
            "text": "Mindfulness begins with breathing.",
            "confidence": 0.88,
            "language": "en",
            "segments": 1,
        }


class FakeStream:
    def __init__(self, chunks: list[bytes | None]) -> None:
        self._chunks = iter(chunks)

    def __enter__(self) -> "FakeStream":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read_chunk(self, timeout: float) -> bytes | None:
        del timeout
        return next(self._chunks, None)


def test_energy_vad_detects_start_and_end() -> None:
    vad = EnergyVoiceActivityDetector(threshold=0.01, start_frames=2, end_frames=2)

    first = vad.process(_pcm_chunk(3000))
    second = vad.process(_pcm_chunk(3000))
    third = vad.process(_pcm_chunk(0))
    fourth = vad.process(_pcm_chunk(0))

    assert first.speech_started is False
    assert second.speech_started is True
    assert third.speech_ended is False
    assert fourth.speech_ended is True


def test_streaming_audio_buffer_keeps_preroll_and_marks_complete() -> None:
    vad = EnergyVoiceActivityDetector(threshold=0.01, start_frames=2, end_frames=2)
    buffer = StreamingAudioBuffer(pre_roll_chunks=2, max_chunks=10)

    events = [
        vad.process(_pcm_chunk(0)),
        vad.process(_pcm_chunk(3000)),
        vad.process(_pcm_chunk(3000)),
        vad.process(_pcm_chunk(0)),
        vad.process(_pcm_chunk(0)),
    ]
    chunks = [
        _pcm_chunk(0),
        _pcm_chunk(3000),
        _pcm_chunk(3000),
        _pcm_chunk(0),
        _pcm_chunk(0),
    ]

    for chunk, event in zip(chunks, events):
        buffer.push(chunk, event)

    assert buffer.is_complete is True
    assert buffer.chunk_count >= 4
    assert buffer.audio_bytes()


def test_speech_recognizer_mock_provider_returns_stub_payload() -> None:
    recognizer = SpeechRecognizer(settings=Settings(speech_provider="mock"))

    payload = recognizer.transcribe()

    assert payload["provider"] == "mock"
    assert payload["status"] == "mock"
    assert payload["text"]
    assert payload["device"]["status"] == "ready"


def test_speech_recognizer_live_provider_uses_buffer_vad_and_transcriber() -> None:
    settings = Settings(
        speech_provider="whisper-local",
        speech_sample_rate=16000,
        speech_channels=1,
        speech_chunk_ms=30,
        speech_pre_roll_ms=60,
        speech_min_speech_ms=60,
        speech_silence_ms=60,
        speech_listen_timeout_seconds=1.0,
        speech_max_utterance_seconds=2.0,
        speech_vad_threshold=0.01,
    )
    transcriber = FakeTranscriber()
    chunks = [
        _pcm_chunk(0),
        _pcm_chunk(3000),
        _pcm_chunk(3000),
        _pcm_chunk(3200),
        _pcm_chunk(0),
        _pcm_chunk(0),
    ]
    recognizer = SpeechRecognizer(
        settings=settings,
        stream_factory=lambda: FakeStream(chunks),
        transcriber=transcriber,
        device_probe=lambda config: {
            "device": "microphone",
            "status": "ready",
            "sample_rate": config.sample_rate,
            "channels": config.channels,
            "provider": "sounddevice",
        },
    )

    payload = recognizer.transcribe()

    assert payload["provider"] == "whisper-local"
    assert payload["status"] == "ok"
    assert payload["text"] == "Mindfulness begins with breathing."
    assert payload["vad"]["speech_started"] is True
    assert payload["vad"]["speech_ended"] is True
    assert payload["audio"]["chunks"] >= 4
    assert len(transcriber.calls) == 1
    assert transcriber.calls[0][1] == 16000
    assert transcriber.calls[0][0]


def test_speech_recognizer_live_provider_returns_idle_without_speech() -> None:
    settings = Settings(
        speech_provider="whisper-local",
        speech_sample_rate=16000,
        speech_channels=1,
        speech_chunk_ms=30,
        speech_pre_roll_ms=60,
        speech_min_speech_ms=60,
        speech_silence_ms=60,
        speech_listen_timeout_seconds=0.0,
        speech_max_utterance_seconds=1.0,
        speech_vad_threshold=0.01,
    )
    transcriber = FakeTranscriber()
    recognizer = SpeechRecognizer(
        settings=settings,
        stream_factory=lambda: FakeStream([None]),
        transcriber=transcriber,
        device_probe=lambda config: {
            "device": "microphone",
            "status": "ready",
            "sample_rate": config.sample_rate,
            "channels": config.channels,
            "provider": "sounddevice",
        },
    )

    payload = recognizer.transcribe()

    assert payload["provider"] == "whisper-local"
    assert payload["status"] == "idle"
    assert payload["text"] == ""
    assert transcriber.calls == []
