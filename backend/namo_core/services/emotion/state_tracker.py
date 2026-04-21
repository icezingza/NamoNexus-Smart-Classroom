"""EmotionStateTracker — rolling window for smooth emotion state transitions.

Prevents rapid flipping between states by maintaining a rolling average
of composite_score over the last N readings before deriving a state label.

Without smoothing, a momentary distraction (one bad frame) would flip the
system from 'focused' to 'distracted', which would confuse the teacher's tone.
"""
from __future__ import annotations

from collections import deque

# Same thresholds as EmotionDetector — single source of truth kept in detector.py
# Duplicated here only for self-contained smoothing logic.
_THRESHOLDS: list[tuple[float, str]] = [
    (0.80, "focused"),
    (0.60, "attentive"),
    (0.40, "wandering"),
    (0.20, "distracted"),
    (0.00, "disengaged"),
]


def _score_to_state(avg_score: float) -> str:
    """Map an averaged composite score to an emotion state label."""
    for min_score, state in _THRESHOLDS:
        if avg_score >= min_score:
            return state
    return "disengaged"


class EmotionStateTracker:
    """Maintains a rolling window of composite scores for smooth transitions.

    Args:
        window: Number of readings to keep in the rolling window (default 5).
    """

    def __init__(self, window: int = 5) -> None:
        self._window = window
        self._scores: deque[float] = deque(maxlen=window)
        self._current_state: str = "attentive"

    def update(self, composite_score: float) -> str:
        """Add a new score reading and return the smoothed state.

        Args:
            composite_score: Latest composite score from EmotionDetector.

        Returns:
            Smoothed emotion state label.
        """
        self._scores.append(composite_score)
        avg = sum(self._scores) / len(self._scores)
        self._current_state = _score_to_state(avg)
        return self._current_state

    def current(self) -> str:
        """Return the current smoothed state without adding a new reading."""
        return self._current_state

    def history(self) -> list[float]:
        """Return the list of stored composite score readings."""
        return list(self._scores)

    def average(self) -> float:
        """Return the current rolling average score (0.0 if no readings yet)."""
        if not self._scores:
            return 0.0
        return round(sum(self._scores) / len(self._scores), 4)
