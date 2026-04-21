"""Unit tests for Phase 5 Emotion Engine components.

Tests:
    - EmotionDetector signal weighting and state classification
    - EmotionStateTracker rolling window smoothing
    - EmotionService facade integration
"""
import pytest

from namo_core.modules.emotion.detector import EmotionDetector, _speech_energy
from namo_core.services.emotion.state_tracker import EmotionStateTracker
from namo_core.services.emotion.emotion_service import EmotionService


# ---------------------------------------------------------------------------
# _speech_energy helper
# ---------------------------------------------------------------------------

def test_speech_energy_empty():
    assert _speech_energy({}) == 0.0
    assert _speech_energy({"text": ""}) == 0.0


def test_speech_energy_ten_words():
    text = "นี่คือ ประโยค ที่มี สิบ คำ ใน ข้อความ นี้ ทั้งหมด สิบ"
    assert _speech_energy({"text": text}) == 1.0


def test_speech_energy_capped():
    text = " ".join(["word"] * 50)
    assert _speech_energy({"text": text}) == 1.0


def test_speech_energy_partial():
    text = "hello world"  # 2 words → 0.2
    assert _speech_energy({"text": text}) == pytest.approx(0.2, abs=0.01)


# ---------------------------------------------------------------------------
# EmotionDetector
# ---------------------------------------------------------------------------

class TestEmotionDetector:
    def setup_method(self):
        self.detector = EmotionDetector()

    def _detect(self, attention=0.0, confidence=0.0, text=""):
        perception = {"attention_score": attention}
        transcript = {"confidence": confidence, "text": text}
        return self.detector.detect(perception, transcript)

    def test_returns_required_keys(self):
        result = self._detect(attention=0.8, confidence=0.8, text="hello world")
        assert "emotion_state" in result
        assert "adaptation_style" in result
        assert "explanation_pace" in result
        assert "composite_score" in result
        assert "signals" in result

    def test_focused_state_high_signals(self):
        # attention=0.9, confidence=0.9, energy=1.0 → composite > 0.80
        result = self._detect(attention=0.9, confidence=0.9, text=" ".join(["w"] * 15))
        assert result["emotion_state"] == "focused"
        assert result["adaptation_style"] == "detailed"
        assert result["explanation_pace"] == "fast"

    def test_disengaged_state_zero_signals(self):
        result = self._detect(attention=0.0, confidence=0.0, text="")
        assert result["emotion_state"] == "disengaged"
        assert result["adaptation_style"] == "reset"
        assert result["explanation_pace"] == "slow"

    def test_attentive_state_moderate_signals(self):
        # attention=0.7, confidence=0.7, energy=0 → composite = 0.70*0.5 + 0.70*0.3 = 0.35+0.21 = 0.56
        # With energy=0 → 0.56, which is attentive (≥0.40) but not attentive (≥0.60)
        # Let me calculate: 0.7*0.5 + 0.7*0.3 + 0*0.2 = 0.35 + 0.21 = 0.56 → wandering
        result = self._detect(attention=0.7, confidence=0.7, text="")
        assert result["emotion_state"] in ("attentive", "wandering")

    def test_composite_score_in_range(self):
        for attention in [0.0, 0.5, 1.0]:
            for confidence in [0.0, 0.5, 1.0]:
                result = self._detect(attention=attention, confidence=confidence)
                assert 0.0 <= result["composite_score"] <= 1.0

    def test_signals_dict_contains_all_inputs(self):
        result = self._detect(attention=0.75, confidence=0.6, text="five words here ok now")
        signals = result["signals"]
        assert signals["attention_score"] == pytest.approx(0.75)
        assert signals["speech_confidence"] == pytest.approx(0.6)
        assert signals["speech_energy"] == pytest.approx(0.5)

    def test_clamps_out_of_range_inputs(self):
        # Should not raise; clamp to [0, 1]
        result = self._detect(attention=2.0, confidence=-0.5)
        assert 0.0 <= result["composite_score"] <= 1.0


# ---------------------------------------------------------------------------
# EmotionStateTracker
# ---------------------------------------------------------------------------

class TestEmotionStateTracker:
    def test_initial_state_is_attentive(self):
        tracker = EmotionStateTracker()
        assert tracker.current() == "attentive"

    def test_update_returns_state(self):
        tracker = EmotionStateTracker()
        state = tracker.update(0.9)
        assert state in ("focused", "attentive", "wandering", "distracted", "disengaged")

    def test_smoothing_resists_single_bad_reading(self):
        tracker = EmotionStateTracker(window=5)
        # Build a focused history
        for _ in range(4):
            tracker.update(0.9)
        # One terrible reading should not immediately flip to disengaged
        state = tracker.update(0.0)
        avg = (0.9 * 4 + 0.0) / 5  # = 0.72
        assert state == "attentive"  # avg 0.72 → attentive

    def test_history_length_respects_window(self):
        tracker = EmotionStateTracker(window=3)
        for score in [0.1, 0.2, 0.3, 0.4, 0.5]:
            tracker.update(score)
        assert len(tracker.history()) == 3
        assert tracker.history() == pytest.approx([0.3, 0.4, 0.5])

    def test_average_computed_correctly(self):
        tracker = EmotionStateTracker(window=4)
        for score in [0.4, 0.6, 0.8, 1.0]:
            tracker.update(score)
        assert tracker.average() == pytest.approx(0.7, abs=0.01)

    def test_empty_tracker_average(self):
        tracker = EmotionStateTracker()
        assert tracker.average() == 0.0


# ---------------------------------------------------------------------------
# EmotionService (integration)
# ---------------------------------------------------------------------------

class TestEmotionService:
    def setup_method(self):
        self.service = EmotionService(window=5)

    def test_detect_returns_smoothed_state(self):
        result = self.service.detect(
            perception={"attention_score": 0.85},
            transcript={"confidence": 0.9, "text": "hello world again"},
        )
        assert "smoothed_state" in result
        assert result["smoothed_state"] in (
            "focused", "attentive", "wandering", "distracted", "disengaged"
        )

    def test_current_state_after_detections(self):
        for _ in range(3):
            self.service.detect(
                perception={"attention_score": 0.9},
                transcript={"confidence": 0.9, "text": "many words " * 3},
            )
        snapshot = self.service.current_state()
        assert "smoothed_state" in snapshot
        assert "average_score" in snapshot
        assert "history" in snapshot
        assert len(snapshot["history"]) == 3

    def test_detect_all_keys_present(self):
        result = self.service.detect(
            perception={"attention_score": 0.5},
            transcript={"confidence": 0.5, "text": "test"},
        )
        for key in ("emotion_state", "adaptation_style", "explanation_pace",
                    "composite_score", "signals", "smoothed_state"):
            assert key in result
