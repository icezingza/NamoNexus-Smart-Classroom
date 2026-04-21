"""Feature flag helpers for NamoOrchestrator.

Provides a single ``FeatureFlags`` dataclass built from ``Settings`` so
that orchestrator code reads clean boolean names rather than inspecting
settings fields repeatedly.
"""
from __future__ import annotations

from dataclasses import dataclass

from namo_core.config.settings import Settings, get_settings


@dataclass(frozen=True)
class FeatureFlags:
    """Immutable snapshot of all feature flags for one orchestrator instance."""

    speech: bool = True
    vision: bool = True
    real_devices: bool = False
    llm_intent: bool = True
    knowledge: bool = True
    empathy_engine: bool = True
    emotion_engine: bool = True
    tts: bool = True
    classroom_control: bool = True

    # Derived convenience flag — device mode label used in snapshots
    device_mode: str = "mock"

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "FeatureFlags":
        s = settings or get_settings()
        # real_devices gate: only enable when setting is True AND device_mode != "mock"
        real_devices = s.enable_real_devices and s.device_mode != "mock"
        return cls(
            speech=s.enable_speech,
            vision=s.enable_vision,
            real_devices=real_devices,
            llm_intent=s.enable_llm_intent,
            knowledge=s.enable_knowledge,
            empathy_engine=s.enable_empathy_engine,
            emotion_engine=s.enable_emotion_engine,
            tts=s.enable_tts,
            classroom_control=s.enable_classroom_control,
            device_mode=s.device_mode,
        )

    def as_dict(self) -> dict:
        return {
            "speech": self.speech,
            "vision": self.vision,
            "real_devices": self.real_devices,
            "llm_intent": self.llm_intent,
            "knowledge": self.knowledge,
            "empathy_engine": self.empathy_engine,
            "emotion_engine": self.emotion_engine,
            "tts": self.tts,
            "classroom_control": self.classroom_control,
            "device_mode": self.device_mode,
        }
