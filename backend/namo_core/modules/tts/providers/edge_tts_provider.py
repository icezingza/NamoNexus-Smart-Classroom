"""Microsoft Edge-TTS provider."""
from __future__ import annotations

import asyncio
import base64
import importlib
import threading
from collections.abc import Coroutine

from namo_core.modules.tts.providers.base import BaseTTSProvider


class EdgeTTSProvider(BaseTTSProvider):
    name = "edge-tts"
    _fallback_voice = "th-TH-NiwatNeural"
    _placeholder_voices = {"", "demo-th"}

    def __init__(self, default_voice: str = _fallback_voice) -> None:
        self.default_voice = self._normalize_voice(default_voice)
        try:
            self._edge_tts = importlib.import_module("edge_tts")
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "edge-tts package is not installed. Install `edge-tts` to enable this provider."
            ) from exc

    def synthesize(self, text: str, voice: str) -> dict:
        resolved_voice = self._normalize_voice(voice)
        audio_bytes = self._run_coroutine(
            self._collect_audio_bytes(text=text, voice=resolved_voice)
        )
        if not audio_bytes:
            raise RuntimeError("Edge-TTS returned no audio data.")

        return {
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
            "audio_format": "mp3",
            "voice": resolved_voice,
            "chars_synthesized": len(text),
            "provider": self.name,
            "status": "ok",
        }

    async def _collect_audio_bytes(self, text: str, voice: str) -> bytes:
        communicate = self._edge_tts.Communicate(text=text, voice=voice)
        audio_chunks = bytearray()

        try:
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    audio_chunks.extend(chunk["data"])
        except Exception as exc:
            raise RuntimeError(f"Edge-TTS synthesis failed: {exc}") from exc

        return bytes(audio_chunks)

    def _normalize_voice(self, voice: str) -> str:
        candidate = voice.strip()
        if candidate.lower() in self._placeholder_voices:
            return self.default_voice if hasattr(self, "default_voice") else self._fallback_voice
        return candidate or self._fallback_voice

    def _run_coroutine(self, coroutine: Coroutine[object, object, bytes]) -> bytes:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        return self._run_coroutine_in_thread(coroutine)

    def _run_coroutine_in_thread(
        self, coroutine: Coroutine[object, object, bytes]
    ) -> bytes:
        result: dict[str, bytes] = {}
        error: dict[str, BaseException] = {}

        def runner() -> None:
            try:
                result["value"] = asyncio.run(coroutine)
            except BaseException as exc:  # pragma: no cover - re-raised below
                error["value"] = exc

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join()

        if "value" in error:
            raise error["value"]
        if "value" not in result:
            raise RuntimeError("Edge-TTS worker thread did not return audio data.")
        return result["value"]
