from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from queue import Empty, Queue
from typing import Any


@dataclass(frozen=True)
class MicrophoneCaptureConfig:
    sample_rate: int = 16000
    channels: int = 1
    chunk_ms: int = 30
    dtype: str = "int16"
    device: int | None = None

    @property
    def blocksize(self) -> int:
        return max(1, int(self.sample_rate * self.chunk_ms / 1000))


def capture_audio_status() -> dict:
    return {
        "device": "microphone",
        "status": "ready",
        "sample_rate": 16000,
        "channels": 1,
    }


def probe_microphone_status(
    config: MicrophoneCaptureConfig | None = None,
) -> dict:
    capture_config = config or MicrophoneCaptureConfig()
    if not find_spec("sounddevice"):
        return {
            "device": "microphone",
            "status": "unavailable",
            "sample_rate": capture_config.sample_rate,
            "channels": capture_config.channels,
            "provider": "sounddevice",
            "error": "sounddevice is not installed",
        }

    import sounddevice as sd

    try:
        device_index, device_info = _resolve_input_device(sd=sd, requested_device=capture_config.device)
    except Exception as exc:
        return {
            "device": "microphone",
            "status": "unavailable",
            "sample_rate": capture_config.sample_rate,
            "channels": capture_config.channels,
            "provider": "sounddevice",
            "error": str(exc),
        }

    return {
        "device": "microphone",
        "status": "ready",
        "sample_rate": capture_config.sample_rate,
        "channels": min(capture_config.channels, int(device_info["max_input_channels"])),
        "provider": "sounddevice",
        "device_index": device_index,
        "name": device_info["name"],
    }


class MicrophoneInputStream:
    def __init__(self, config: MicrophoneCaptureConfig) -> None:
        self.config = config
        self._queue: Queue[bytes] = Queue()
        self._stream: Any | None = None
        self._device_index: int | None = None
        self._sounddevice: Any | None = None

    def __enter__(self) -> "MicrophoneInputStream":
        if not find_spec("sounddevice"):
            raise RuntimeError("sounddevice is not installed")

        import sounddevice as sd

        self._sounddevice = sd
        self._device_index, _ = _resolve_input_device(
            sd=sd,
            requested_device=self.config.device,
        )
        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            blocksize=self.config.blocksize,
            channels=self.config.channels,
            dtype=self.config.dtype,
            device=self._device_index,
            callback=self._on_audio,
        )
        self._stream.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def read_chunk(self, timeout: float) -> bytes | None:
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None

    def close(self) -> None:
        if self._stream is None:
            return

        self._stream.stop()
        self._stream.close()
        self._stream = None

    def _on_audio(self, indata, frames, time_info, status) -> None:
        del frames, time_info, status
        self._queue.put(indata.copy().tobytes())


def _resolve_input_device(sd, requested_device: int | None) -> tuple[int, dict]:
    if requested_device is not None:
        device_info = sd.query_devices(requested_device, "input")
        return int(requested_device), dict(device_info)

    default_device = sd.default.device
    candidate_indexes: list[int] = []

    if isinstance(default_device, (list, tuple)) and default_device:
        input_index = default_device[0]
        if input_index is not None and int(input_index) >= 0:
            candidate_indexes.append(int(input_index))

    for index, device_info in enumerate(sd.query_devices()):
        if int(device_info["max_input_channels"]) > 0 and index not in candidate_indexes:
            candidate_indexes.append(index)

    for index in candidate_indexes:
        device_info = dict(sd.query_devices(index))
        if int(device_info["max_input_channels"]) > 0:
            return index, device_info

    raise RuntimeError("No input-capable microphone device found.")
