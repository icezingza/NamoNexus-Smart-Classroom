"""ResonanceEngine — Phase 5 upgrade: three-signal resonance score.

Blends three signals to produce a more nuanced resonance_score:
    attention_score (vision):   50 %  – how focused the student looks
    speech confidence (STT):    30 %  – clarity / certainty of speech
    speech energy (derived):    20 %  – engagement proxy from word count

Previously used only attention (60 %) + confidence (40 %).
The added speech-energy signal helps detect passive silence vs. active engagement.
"""
from __future__ import annotations

from namo_core.core.base_engine import BaseEngine

_MAX_SCORE: float = 0.98
_ATTENTION_W: float = 0.50
_CONFIDENCE_W: float = 0.30
_ENERGY_W: float = 0.20


def _speech_energy(transcript: dict) -> float:
    """Estimate speech engagement energy from transcript word count.

    Args:
        transcript: Dict with optional 'text' key from SpeechRecognizer.

    Returns:
        Normalised energy in [0.0, 1.0]; 10+ words maps to 1.0.
    """
    text: str = (transcript.get("text") or "")
    word_count = len(text.split())
    return min(1.0, word_count / 10.0)


class ResonanceEngine(BaseEngine):
    """Computes resonance_score from vision, speech, and energy signals."""

    name = "resonance"

    def process(self, payload: dict) -> dict:
        """Compute a blended resonance score from available perception signals.

        Args:
            payload: Must contain 'perception' dict (attention_score) and
                     'transcript' dict (confidence, text).

        Returns:
            Payload enriched with resonance_score (float, 0.0–0.98).
        """
        perception: dict = payload.get("perception", {}) or {}
        transcript: dict = payload.get("transcript", {}) or {}

        attention: float = float(perception.get("attention_score", 0.84))
        confidence: float = float(transcript.get("confidence", 0.84))
        energy: float = _speech_energy(transcript)

        raw_score: float = (
            (attention * _ATTENTION_W)
            + (confidence * _CONFIDENCE_W)
            + (energy * _ENERGY_W)
        )
        score: float = round(min(max(raw_score, 0.0), _MAX_SCORE), 4)

        updated = dict(payload)
        updated["resonance_score"] = score
        return updated
