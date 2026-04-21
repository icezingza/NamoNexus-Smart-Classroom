from __future__ import annotations

import time
from collections.abc import Callable

from namo_core.config.settings import Settings, get_settings
from namo_core.devices.microphone.capture import (
    MicrophoneCaptureConfig,
    MicrophoneInputStream,
    capture_audio_status,
    probe_microphone_status,
)
from namo_core.modules.speech.streaming_buffer import StreamingAudioBuffer
from namo_core.modules.speech.transcriber import (
    FasterWhisperTranscriber,
    MockSpeechTranscriber,
    WhisperSpeechTranscriber,
)
from namo_core.modules.speech.vad import EnergyVoiceActivityDetector, VoiceActivityEvent


class SpeechRecognizer:
    def __init__(
        self,
        settings: Settings | None = None,
        stream_factory: Callable[[], MicrophoneInputStream] | None = None,
        transcriber=None,
        device_probe: Callable[[MicrophoneCaptureConfig], dict] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.configured_provider = self.settings.speech_provider.lower()
        self.capture_config = MicrophoneCaptureConfig(
            sample_rate=self.settings.speech_sample_rate,
            channels=self.settings.speech_channels,
            chunk_ms=self.settings.speech_chunk_ms,
        )
        self.stream_factory = stream_factory or (lambda: MicrophoneInputStream(self.capture_config))
        self.device_probe = device_probe or probe_microphone_status
        self._fallback_reason: str | None = None
        self.transcriber = transcriber or self._build_transcriber()
        self.provider_name = getattr(self.transcriber, "name", self.configured_provider)
        self.vad = EnergyVoiceActivityDetector(
            threshold=self.settings.speech_vad_threshold,
            start_frames=max(1, self.settings.speech_min_speech_ms // self.settings.speech_chunk_ms),
            end_frames=max(1, self.settings.speech_silence_ms // self.settings.speech_chunk_ms),
        )

    def transcribe(self) -> dict:
        if self.provider_name == "mock":
            return self._mock_payload()

        device_status = self.device_probe(self.capture_config)
        if device_status.get("status") != "ready":
            payload = self._empty_payload(device_status=device_status, status="unavailable")
            if self._fallback_reason:
                payload["fallback_reason"] = self._fallback_reason
            return payload

        try:
            payload = self._transcribe_live(device_status=device_status)
        except Exception as exc:
            payload = self._empty_payload(device_status=device_status, status="error")
            payload["error"] = str(exc)

        if self._fallback_reason:
            payload["fallback_reason"] = self._fallback_reason
        return payload

    def _build_transcriber(self):
        if self.configured_provider in {"mock", ""}:
            return MockSpeechTranscriber()

        if self.configured_provider in {"whisper-local", "whisper", "real"}:
            return WhisperSpeechTranscriber(
                model_name=self.settings.speech_model,
                language=self.settings.speech_language,
            )

        if self.configured_provider == "faster-whisper":
            return FasterWhisperTranscriber(
                model_name=self.settings.speech_model,
                language=self.settings.speech_language,
            )

        if self.configured_provider == "google-cloud":
            try:
                from namo_core.modules.speech.transcriber import GoogleSTTTranscriber
                return GoogleSTTTranscriber(language=self.settings.speech_language)
            except Exception as exc:
                self._fallback_reason = f"Google STT init failed ({exc}), falling back to mock."
                return MockSpeechTranscriber()

        self._fallback_reason = (
            f"Unsupported speech provider '{self.settings.speech_provider}'; using mock provider."
        )
        return MockSpeechTranscriber()

    def _mock_payload(self) -> dict:
        status = capture_audio_status()
        transcript = self.transcriber.transcribe_pcm16(
            audio_bytes=b"",
            sample_rate=self.capture_config.sample_rate,
        )
        return {
            "text": transcript["text"],
            "confidence": transcript["confidence"],
            "device": status,
            "provider": self.provider_name,
            "status": "mock",
            "vad": {
                "speech_started": False,
                "speech_ended": False,
                "last_energy": 0.0,
                "threshold": self.settings.speech_vad_threshold,
                "state": "mock",
            },
            "audio": {
                "sample_rate": self.capture_config.sample_rate,
                "channels": self.capture_config.channels,
                "chunk_ms": self.capture_config.chunk_ms,
                "chunks": 0,
                "duration_ms": 0,
            },
        }

    def _transcribe_live(self, device_status: dict) -> dict:
        self.vad.reset()
        pre_roll_chunks = max(0, self.settings.speech_pre_roll_ms // self.settings.speech_chunk_ms)
        max_chunks = max(
            1,
            int((self.settings.speech_max_utterance_seconds * 1000) // self.settings.speech_chunk_ms),
        )
        buffer = StreamingAudioBuffer(pre_roll_chunks=pre_roll_chunks, max_chunks=max_chunks)
        listen_deadline = time.monotonic() + max(0.0, self.settings.speech_listen_timeout_seconds)
        chunk_timeout = max(self.capture_config.chunk_ms / 1000 * 2, 0.1)
        last_event = VoiceActivityEvent(
            is_speech=False,
            speech_started=False,
            speech_ended=False,
            in_speech=False,
            energy=0.0,
        )
        speech_started = False
        speech_ended = False

        with self.stream_factory() as stream:
            while True:
                chunk = stream.read_chunk(timeout=chunk_timeout)
                now = time.monotonic()

                if chunk is None:
                    if not buffer.is_active and now >= listen_deadline:
                        return self._empty_payload(
                            device_status=device_status,
                            status="idle",
                            last_event=last_event,
                        )
                    continue

                last_event = self.vad.process(chunk)
                buffer.push(chunk=chunk, event=last_event)
                speech_started = speech_started or last_event.speech_started
                speech_ended = speech_ended or last_event.speech_ended

                if buffer.is_complete:
                    break

                if not speech_started and now >= listen_deadline:
                    return self._empty_payload(
                        device_status=device_status,
                        status="idle",
                        last_event=last_event,
                    )

        audio_bytes = buffer.audio_bytes()
        if not audio_bytes:
            return self._empty_payload(
                device_status=device_status,
                status="idle",
                last_event=last_event,
            )

        transcript = self.transcriber.transcribe_pcm16(
            audio_bytes=audio_bytes,
            sample_rate=self.capture_config.sample_rate,
        )
        payload = {
            "text": transcript.get("text", ""),
            "confidence": transcript.get("confidence", 0.0),
            "device": device_status,
            "provider": self.provider_name,
            "status": "ok" if transcript.get("text") else "no-match",
            "vad": {
                "speech_started": speech_started,
                "speech_ended": speech_ended,
                "last_energy": round(last_event.energy, 6),
                "threshold": self.settings.speech_vad_threshold,
                "state": "speech-ended" if speech_ended else "captured",
            },
            "audio": {
                "sample_rate": self.capture_config.sample_rate,
                "channels": self.capture_config.channels,
                "chunk_ms": self.capture_config.chunk_ms,
                "chunks": buffer.chunk_count,
                "duration_ms": buffer.duration_ms(self.capture_config.chunk_ms),
            },
        }
        language = transcript.get("language")
        if language:
            payload["language"] = language
        if "segments" in transcript:
            payload["segments"] = transcript["segments"]
        return payload

    def _empty_payload(
        self,
        device_status: dict,
        status: str,
        last_event: VoiceActivityEvent | None = None,
    ) -> dict:
        event = last_event or VoiceActivityEvent(
            is_speech=False,
            speech_started=False,
            speech_ended=False,
            in_speech=False,
            energy=0.0,
        )
        return {
            "text": "",
            "confidence": 0.0,
            "device": device_status,
            "provider": self.provider_name,
            "status": status,
            "vad": {
                "speech_started": False,
                "speech_ended": False,
                "last_energy": round(event.energy, 6),
                "threshold": self.settings.speech_vad_threshold,
                "state": status,
            },
            "audio": {
                "sample_rate": self.capture_config.sample_rate,
                "channels": self.capture_config.channels,
                "chunk_ms": self.capture_config.chunk_ms,
                "chunks": 0,
                "duration_ms": 0,
            },
        }
