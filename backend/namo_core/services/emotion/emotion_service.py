"""EmotionService — Phase 5: Emotion Engine facade.

Single entry point for querying student emotional state.
Wraps EmotionDetector and EmotionStateTracker so callers do not
need to manage smoothing state themselves.

Typical usage in the orchestrator:
    emotion_svc = EmotionService()
    result = emotion_svc.detect(perception, transcript)
    # result["smoothed_state"] is the stable state for teaching adaptation
"""
from __future__ import annotations

from namo_core.modules.emotion.detector import EmotionDetector
from namo_core.services.emotion.state_tracker import EmotionStateTracker


class EmotionService:
    """High-level facade for student emotion detection and state tracking."""

    def __init__(self, window: int = 5) -> None:
        self._detector = EmotionDetector()
        self._tracker = EmotionStateTracker(window=window)

    def detect(self, perception: dict, transcript: dict) -> dict:
        """Detect emotion from the latest perception and speech signals.

        Runs EmotionDetector and passes the composite_score through the
        rolling-window StateTracker to produce a smoothed state label.

        Args:
            perception: Output of VisionAnalyzer.analyze_frame().
            transcript: Output of SpeechRecognizer (contains 'confidence', 'text').

        Returns:
            Raw detection dict plus 'smoothed_state' key.
        """
        raw = self._detector.detect(perception=perception, transcript=transcript)
        smoothed_state = self._tracker.update(raw["composite_score"])
        return {**raw, "smoothed_state": smoothed_state}

    def current_state(self) -> dict:
        """Return the most recent tracked state without running a new detection.

        Returns:
            Dict with 'smoothed_state', 'average_score', and 'history' keys.
        """
        return {
            "smoothed_state": self._tracker.current(),
            "average_score": self._tracker.average(),
            "history": self._tracker.history(),
        }
