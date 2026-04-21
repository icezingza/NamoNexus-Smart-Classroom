"""EmpathyEngine — Phase 5: Emotion-aware empathy signal processor.

Maps composite resonance signal to teacher tone, student state, and a
teaching_hint that the ReasoningService injects into the LLM system prompt
so explanations adapt to the student's current engagement level.

State thresholds (resonance_score):
    warm      ≥ 0.80  focused    → rich, referenced Dhamma explanation
    calm      ≥ 0.60  attentive  → clear, steady teaching with one example
    gentle    ≥ 0.40  wandering  → brief answer + engaging question
    concerned ≥ 0.20  distracted → short story / analogy approach
    patient   < 0.20  disengaged → pause, greet, ask how the student feels
"""
from __future__ import annotations

from namo_core.core.base_engine import BaseEngine

# (min_resonance, tone, student_state, teaching_hint)
_STATES: list[tuple[float, str, str, str]] = [
    (
        0.80,
        "warm",
        "focused",
        "อธิบายธรรมะอย่างละเอียดพร้อมอ้างอิงพระไตรปิฎก ใช้ภาษาที่ชัดเจนและมีตัวอย่างเชิงลึก",
    ),
    (
        0.60,
        "calm",
        "attentive",
        "อธิบายด้วยความชัดเจนในจังหวะปกติ พร้อมตัวอย่างหนึ่งอย่างที่เข้าใจง่าย",
    ),
    (
        0.40,
        "gentle",
        "wandering",
        "ตอบสั้นๆ ตรงประเด็น จบด้วยคำถามกระตุ้นความสนใจเพื่อดึงสมาธิกลับมา",
    ),
    (
        0.20,
        "concerned",
        "distracted",
        "เล่านิทานชาดกหรืออุปมาสั้นๆ หลีกเลี่ยงศัพท์เทคนิค ใช้ภาษาเด็กเข้าใจง่าย",
    ),
    (
        0.00,
        "patient",
        "disengaged",
        "หยุดบทเรียน ทักทายนักเรียนด้วยความอบอุ่น ถามว่าเป็นอย่างไรบ้างก่อนเริ่มใหม่",
    ),
]


class EmpathyEngine(BaseEngine):
    """Maps resonance + emotion signals to tone, student state, and teaching hint."""

    name = "empathy"

    def process(self, payload: dict) -> dict:
        """Process resonance score and enrich payload with tone and teaching guidance.

        Args:
            payload: Must contain resonance_score (float, 0–1).
                     May contain emotion_state from EmotionDetector for override.

        Returns:
            Enriched payload adding:
                tone          – teacher's voice tone (warm/calm/gentle/concerned/patient)
                student_state – current engagement label
                teaching_hint – Thai-language instruction for LLM system prompt
        """
        score: float = float(payload.get("resonance_score", 0.84))
        score = min(1.0, max(0.0, score))

        tone = "patient"
        student_state = "disengaged"
        teaching_hint = _STATES[-1][3]

        for min_score, candidate_tone, candidate_state, hint in _STATES:
            if score >= min_score:
                tone = candidate_tone
                student_state = candidate_state
                teaching_hint = hint
                break

        # EmotionDetector provides richer state — use it when available
        if payload.get("emotion_state"):
            student_state = payload["emotion_state"]

        updated = dict(payload)
        updated["tone"] = tone
        updated["student_state"] = student_state
        updated["teaching_hint"] = teaching_hint
        return updated

    @staticmethod
    def modifier_from_text_emotion(emotion: str) -> str:
        """แปลง text emotion → prompt modifier สำหรับ inject เข้า LLM

        Args:
            emotion: ผลจาก TextEmotionAnalyzer (frustrated/confused/happy/neutral)

        Returns:
            คำสั่งภาษาไทยสำหรับ prepend เข้า system prompt
        """
        _MAP = {
            "frustrated": (
                "ผู้ใช้กำลังท้อและรู้สึกยากลำบาก "
                "ให้ตอบด้วยความเห็นอกเห็นใจและให้กำลังใจก่อนสอน "
                "ใช้ภาษาอ่อนโยน ย่อยเนื้อหาเป็นขั้นเล็กๆ "
                "และยืนยันว่าความรู้สึกนี้เป็นเรื่องปกติมากๆ"
            ),
            "confused": (
                "ผู้ใช้กำลังสับสนและไม่เข้าใจ "
                "ให้อธิบายใหม่ตั้งแต่ต้นด้วยภาษาง่ายที่สุด "
                "ใช้ตัวอย่างในชีวิตประจำวัน หลีกเลี่ยงศัพท์บาลีและเทคนิค"
            ),
            "happy": (
                "ผู้ใช้มีความสุขและกระตือรือร้น "
                "ตอบด้วยพลังงานบวก สามารถขยายความลึกขึ้นและเพิ่มเนื้อหาพิเศษได้"
            ),
            "neutral": (
                "ผู้ใช้อยู่ในสภาวะปกติ "
                "ตอบชัดเจนตรงประเด็นด้วยภาษาพูดแบบเป็นกันเอง"
            ),
        }
        return _MAP.get(emotion, _MAP["neutral"])
