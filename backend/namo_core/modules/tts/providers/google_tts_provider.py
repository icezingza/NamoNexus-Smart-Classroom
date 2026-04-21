"""Google Cloud TTS provider for GCP Hybrid Expansion."""
from __future__ import annotations

import base64
import importlib
import logging

from namo_core.modules.tts.providers.base import BaseTTSProvider

logger = logging.getLogger(__name__)

class GoogleTTSProvider(BaseTTSProvider):
    name = "google-cloud"
    _fallback_voice = "th-TH-Neural2-C"
    _placeholder_voices = {"", "demo-th"}

    def __init__(self, default_voice: str = _fallback_voice) -> None:
        self.default_voice = self._normalize_voice(default_voice)
        try:
            self._texttospeech = importlib.import_module("google.cloud.texttospeech")
            self.client = self._texttospeech.TextToSpeechClient()
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "google-cloud-texttospeech package is not installed."
            ) from exc
        except Exception as exc:
            logger.warning("Google Cloud credentials not found. Ensure GOOGLE_APPLICATION_CREDENTIALS is set.")
            raise RuntimeError(f"GCP init failed: {exc}") from exc

    def synthesize(self, text: str, voice: str) -> dict:
        resolved_voice = self._normalize_voice(voice)
        
        synthesis_input = self._texttospeech.SynthesisInput(text=text)
        
        # Parse voice name e.g. "th-TH-Neural2-C" -> lang="th-TH"
        lang_code = resolved_voice[:5] if len(resolved_voice) >= 5 else "th-TH"
        
        voice_params = self._texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            name=resolved_voice
        )
        
        audio_config = self._texttospeech.AudioConfig(
            audio_encoding=self._texttospeech.AudioEncoding.MP3
        )
        
        try:
            response = self.client.synthesize_speech(
                input=synthesis_input, 
                voice=voice_params, 
                audio_config=audio_config
            )
            audio_bytes = response.audio_content
        except Exception as exc:
            raise RuntimeError(f"Google TTS synthesis failed: {exc}") from exc

        if not audio_bytes:
            raise RuntimeError("Google TTS returned no audio data.")

        return {
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
            "audio_format": "mp3",
            "voice": resolved_voice,
            "chars_synthesized": len(text),
            "provider": self.name,
            "status": "ok",
        }

    def _normalize_voice(self, voice: str) -> str:
        candidate = voice.strip()
        if candidate.lower() in self._placeholder_voices:
            return self.default_voice if hasattr(self, "default_voice") else self._fallback_voice
        return candidate or self._fallback_voice
