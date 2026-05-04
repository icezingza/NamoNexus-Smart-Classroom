"""Emotion API routes — Phase 5: Emotion Engine.

Exposes the current student emotion state detected by the Emotion Engine.
The dashboard polls this endpoint to show real-time engagement indicators
and to inform the teacher when a student's attention is dropping.

Endpoints:
    GET /emotion/state  – latest emotion snapshot from sensor signals
"""
from __future__ import annotations

from fastapi import APIRouter

from namo_core.modules.vision.analyzer import VisionAnalyzer
from namo_core.services.emotion.emotion_service import EmotionService

router = APIRouter(prefix="/emotion", tags=["emotion"])

# Module-level singletons so the StateTracker window persists across requests.
_emotion_service = EmotionService(window=5)
_vision = VisionAnalyzer()


@router.get("/state")
async def get_emotion_state() -> dict:
    """Return the current student emotion state from the latest sensor snapshot.

    Uses VisionAnalyzer for the perception signal and a neutral transcript
    (live speech is handled separately via the /nexus pipeline).
    The rolling-window tracker smooths rapid fluctuations across calls.

    Returns:
        JSON with:
            status         – "ok"
            emotion_state  – raw detected state (focused/attentive/…/disengaged)
            smoothed_state – rolling-window smoothed state (more stable)
            adaptation_style – suggested teaching style for this state
            explanation_pace – fast/normal/slow
            composite_score  – weighted blend of all signals [0.0, 1.0]
            signals          – individual signal values for transparency
    """
    perception = _vision.analyze_frame()
    # Neutral transcript: no live speech data at this endpoint
    transcript: dict = {"text": "", "confidence": 0.5}
    result = _emotion_service.detect(perception=perception, transcript=transcript)
    return {"status": "ok", **result}
