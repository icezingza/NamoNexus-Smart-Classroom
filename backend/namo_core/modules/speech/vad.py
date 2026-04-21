"""Voice activity detection helpers."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class VoiceActivityEvent:
    is_speech: bool
    speech_started: bool
    speech_ended: bool
    in_speech: bool
    energy: float


class EnergyVoiceActivityDetector:
    def __init__(self, threshold: float, start_frames: int, end_frames: int) -> None:
        self.threshold = threshold
        self.start_frames = max(1, start_frames)
        self.end_frames = max(1, end_frames)
        self.reset()

    def reset(self) -> None:
        self._speech_frames = 0
        self._silence_frames = 0
        self._in_speech = False

    def process(self, chunk: bytes) -> VoiceActivityEvent:
        energy = self._rms(chunk)
        is_speech = energy >= self.threshold
        speech_started = False
        speech_ended = False

        if self._in_speech:
            if is_speech:
                self._silence_frames = 0
            else:
                self._silence_frames += 1
                if self._silence_frames >= self.end_frames:
                    self._in_speech = False
                    self._speech_frames = 0
                    self._silence_frames = 0
                    speech_ended = True
        else:
            if is_speech:
                self._speech_frames += 1
                if self._speech_frames >= self.start_frames:
                    self._in_speech = True
                    self._silence_frames = 0
                    speech_started = True
            else:
                self._speech_frames = 0

        return VoiceActivityEvent(
            is_speech=is_speech,
            speech_started=speech_started,
            speech_ended=speech_ended,
            in_speech=self._in_speech,
            energy=energy,
        )

    def _rms(self, chunk: bytes) -> float:
        samples = np.frombuffer(chunk, dtype=np.int16)
        if samples.size == 0:
            return 0.0

        normalized = samples.astype(np.float32) / 32768.0
        return float(np.sqrt(np.mean(normalized * normalized)))
