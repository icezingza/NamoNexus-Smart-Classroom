"""Reasoning API routes.

Provides LLM-powered Dhamma explanation and chat endpoints.

Phase 5 addition: Both endpoints accept an optional ``student_state``
query parameter. When provided, the matching teaching_hint from
EmpathyEngine is resolved and injected into the LLM context so responses
adapt to the student's current engagement level.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from namo_core.config.settings import get_settings
from namo_core.services.reasoning.reasoner import ReasoningService

router = APIRouter(prefix="/reasoning", tags=["reasoning"])

# ── Singleton — โหลด FAISS + model ครั้งเดียวตลอด process lifetime ──
_reasoner: ReasoningService | None = None


def get_reasoner() -> ReasoningService:
    global _reasoner
    if _reasoner is None:
        _reasoner = ReasoningService()
    return _reasoner

# Teaching hints keyed by student_state label (mirrors EmpathyEngine._STATES)
_HINT_BY_STATE: dict[str, str] = {
    "focused":    "อธิบายธรรมะอย่างละเอียดพร้อมอ้างอิงพระไตรปิฎก ใช้ภาษาที่ชัดเจนและมีตัวอย่างเชิงลึก",
    "attentive":  "อธิบายด้วยความชัดเจนในจังหวะปกติ พร้อมตัวอย่างหนึ่งอย่างที่เข้าใจง่าย",
    "wandering":  "ตอบสั้นๆ ตรงประเด็น จบด้วยคำถามกระตุ้นความสนใจเพื่อดึงสมาธิกลับมา",
    "distracted": "เล่านิทานชาดกหรืออุปมาสั้นๆ หลีกเลี่ยงศัพท์เทคนิค ใช้ภาษาเด็กเข้าใจง่าย",
    "disengaged": "หยุดบทเรียน ทักทายนักเรียนด้วยความอบอุ่น ถามว่าเป็นอย่างไรบ้างก่อนเริ่มใหม่",
}


class ExplainRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class ChatRequest(BaseModel):
    messages: list[dict] = Field(min_length=1)


def _maybe_attach_tts(result: dict, speak: bool) -> dict:
    if speak and get_settings().enable_tts:
        from namo_core.modules.tts.synthesizer import SpeechSynthesizer

        answer_text = result.get("answer", "")
        if answer_text:
            result["tts"] = SpeechSynthesizer().speak(text=answer_text)
    return result


@router.post("/explain")
def explain(
    payload: ExplainRequest,
    speak: bool = Query(default=False, description="Auto-synthesize the answer via TTS"),
    student_state: str = Query(
        default="",
        description="Current student emotion state for teaching adaptation "
                    "(focused/attentive/wandering/distracted/disengaged)",
    ),
) -> dict:
    """Generate a Dhamma explanation adapted to the student's emotion state."""
    teaching_hint = _HINT_BY_STATE.get(student_state, "")
    result = get_reasoner().explain(payload.query.strip(), teaching_hint=teaching_hint)
    if student_state:
        result["student_state"] = student_state
    return _maybe_attach_tts(result=result, speak=speak)


@router.post("/chat")
def chat(
    payload: ChatRequest,
    speak: bool = Query(default=False, description="Auto-synthesize the answer via TTS"),
    student_state: str = Query(
        default="",
        description="Current student emotion state for teaching adaptation",
    ),
) -> dict:
    """Run a multi-turn Dhamma chat session adapted to the student's emotion state."""
    teaching_hint = _HINT_BY_STATE.get(student_state, "")
    result = get_reasoner().chat(payload.messages, teaching_hint=teaching_hint)
    if student_state:
        result["student_state"] = student_state
    return _maybe_attach_tts(result=result, speak=speak)
