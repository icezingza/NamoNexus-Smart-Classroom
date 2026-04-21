"""Multi-signal emotion detector for Phase 5 - Emotion Engine.

Combines visual attention, speech confidence, and speech energy signals
to classify student emotional state and determine the appropriate
adaptation style for the Dhamma teaching session.

State thresholds (composite_score):
    focused    ≥ 0.80 → detailed explanation with Tripitaka references
    attentive  ≥ 0.60 → standard clear explanation
    wandering  ≥ 0.40 → concise + engaging question to re-focus
    distracted ≥ 0.20 → story-based / simplified language
    disengaged < 0.20 → pause and reset signal
"""
from __future__ import annotations

# Mathematical Invariant (Golden Ratio)
PHI = 1.6180339887

# (min_score, emotion_state, adaptation_style, explanation_pace)
# Using Bayesian invariant thresholds based on Golden Ratio inverses
_STATES: list[tuple[float, str, str, str]] = [
    (1.0 / PHI,         "focused",    "detailed",    "fast"),      # ~0.618
    (1.0 / (PHI ** 2),  "attentive",  "standard",    "normal"),    # ~0.382
    (1.0 / (PHI ** 3),  "wandering",  "concise",     "normal"),    # ~0.236
    (1.0 / (PHI ** 4),  "distracted", "story_based", "slow"),      # ~0.146
    (0.00,              "disengaged", "reset",       "slow"),
]


def _speech_energy(transcript: dict) -> float:
    """Derive speech engagement energy from transcript word count.

    More words spoken ≈ higher engagement. Capped at 10 words → 1.0.

    Args:
        transcript: Dict containing optional 'text' field from SpeechRecognizer.

    Returns:
        Normalised energy score in [0.0, 1.0].
    """
    text: str = transcript.get("text", "") or ""
    word_count = len(text.split())
    return round(min(1.0, word_count / 10.0), 4)


class TextEmotionAnalyzer:
    """วิเคราะห์อารมณ์จาก Text ภาษาไทย (keyword-based, ไม่ต้องใช้ ML model)

    Returns one of: frustrated / confused / happy / neutral
    """

    _RULES: list[tuple[str, list[str]]] = [
        ("frustrated", ["ท้อ", "เหนื่อย", "หมดแรง", "ยากขนาดนี้", "ทำไมมัน", "ทำไมถึง", "ทำไมต้อง", "ไม่ไหวแล้ว", "หัวร้อน", "짜증"]),
        ("confused",   ["ไม่รู้เรื่อง", "ไม่เข้าใจ", "งงมาก", "งงเลย", "สับสน", "ไม่ชัด", "ไม่แน่ใจ", "หมายความว่า"]),
        ("happy",      ["ดีใจ", "สนุก", "เข้าใจแล้ว", "ชอบมาก", "เยี่ยม", "เจ๋ง", "ขอบคุณ", "ยอดเยี่ยม"]),
    ]

    def analyze(self, text: str) -> dict:
        """วิเคราะห์อารมณ์จาก string

        Args:
            text: ข้อความจากผู้ใช้

        Returns:
            dict: emotion, confidence, matched_keywords
        """
        text_lower = text.lower()
        scores: dict[str, int] = {}
        matched: dict[str, list[str]] = {}

        for emotion, keywords in self._RULES:
            hits = [kw for kw in keywords if kw in text_lower]
            if hits:
                scores[emotion] = len(hits)
                matched[emotion] = hits

        if not scores:
            return {"emotion": "neutral", "confidence": 0.5, "matched_keywords": []}

        top = max(scores, key=lambda e: scores[e])
        conf = round(min(1.0, 0.5 + scores[top] * 0.15), 3)
        return {"emotion": top, "confidence": conf, "matched_keywords": matched[top]}


class EmotionDetector:
    """
    Combines perception and speech signals into a composite emotion score.

    Bayesian prior weights mapped to Golden Ratio invariant:
    1/PHI + 1/PHI^3 + 1/PHI^4 = 1.0
    """

    # Bayesian prior weights mapped to Golden Ratio invariant
    # 1/PHI + 1/PHI^3 + 1/PHI^4 = 1.0
    _ATTENTION_WEIGHT: float = 1.0 / PHI            # ~0.6180
    _CONFIDENCE_WEIGHT: float = 1.0 / (PHI ** 3)    # ~0.2360
    _ENERGY_WEIGHT: float = 1.0 / (PHI ** 4)        # ~0.1458

    def detect(self, perception: dict, transcript: dict) -> dict:
        """Detect student emotion state from multi-modal signals.

        Args:
            perception: Output from VisionAnalyzer (expects 'attention_score').
            transcript: Output from SpeechRecognizer (expects 'confidence', 'text').

        Returns:
            dict with keys:
                emotion_state    - one of focused/attentive/wandering/distracted/disengaged
                adaptation_style - one of detailed/standard/concise/story_based/reset
                explanation_pace - fast/normal/slow
                composite_score  - weighted blend in [0.0, 1.0]
                signals          - raw input values for transparency
        """
        attention: float = min(1.0, max(0.0, float(perception.get("attention_score", 0.0))))
        confidence: float = min(1.0, max(0.0, float(transcript.get("confidence", 0.0))))
        energy: float = _speech_energy(transcript)

        composite: float = round(
            (attention * self._ATTENTION_WEIGHT)
            + (confidence * self._CONFIDENCE_WEIGHT)
            + (energy * self._ENERGY_WEIGHT),
            4,
        )
        composite = min(1.0, max(0.0, composite))

        emotion_state, adaptation_style, explanation_pace = "disengaged", "reset", "slow"
        for min_score, state, style, pace in _STATES:
            if composite >= min_score:
                emotion_state, adaptation_style, explanation_pace = state, style, pace
                break

        return {
            "emotion_state": emotion_state,
            "adaptation_style": adaptation_style,
            "explanation_pace": explanation_pace,
            "composite_score": composite,
            "signals": {
                "attention_score": attention,
                "speech_confidence": confidence,
                "speech_energy": energy,
            },
        }


