"""Chunk buffer for low-latency speech capture."""
from __future__ import annotations

from collections import deque

from namo_core.modules.speech.vad import VoiceActivityEvent


class StreamingAudioBuffer:
    def __init__(self, pre_roll_chunks: int, max_chunks: int) -> None:
        self.max_chunks = max(1, max_chunks)
        self._pre_roll = deque(maxlen=max(0, pre_roll_chunks))
        self._captured: list[bytes] = []
        self._active = False
        self._complete = False

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def is_complete(self) -> bool:
        return self._complete

    @property
    def chunk_count(self) -> int:
        return len(self._captured)

    def push(self, chunk: bytes, event: VoiceActivityEvent) -> None:
        if not self._active:
            self._pre_roll.append(chunk)
            if event.speech_started:
                self._active = True
                self._captured.extend(self._pre_roll)
                self._pre_roll.clear()
        else:
            self._captured.append(chunk)

        if self._active and (event.speech_ended or len(self._captured) >= self.max_chunks):
            self._complete = True

    def audio_bytes(self) -> bytes:
        return b"".join(self._captured)

    def duration_ms(self, chunk_ms: int) -> int:
        return self.chunk_count * chunk_ms
