"""Classroom API routes — Phase 6: Full classroom interaction control.

Endpoints:
    GET  /classroom/session           – current session state
    PATCH /classroom/session          – update session metadata
    POST /classroom/session/start     – start a lesson session   [Phase 6]
    POST /classroom/session/end       – end current session      [Phase 6]

    GET  /classroom/slide             – current slide position
    GET  /classroom/slide/content     – current slide full content [Phase 6]
    POST /classroom/slide/next        – advance slide
    POST /classroom/slide/prev        – previous slide
    POST /classroom/slide/{slide_n}   – jump to slide

    GET  /classroom/projector         – projector status
    POST /classroom/projector/{mode}  – set projector mode

    POST /classroom/student/connect   – student joins           [Phase 6]
    POST /classroom/student/disconnect – student leaves         [Phase 6]
    GET  /classroom/students          – student roster          [Phase 6]

    POST /classroom/assistant/{state} – transition assistant state [Phase 6]

    GET  /classroom/events            – event log               [Phase 6]
    GET  /classroom/lessons           – available lessons list  [Phase 6]
    POST /classroom/session/{id}/generate-summary – AI Session Analytics [New Feature]
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from namo_core.modules.classroom.projector_controller import ProjectorController
from namo_core.modules.classroom.slide_controller import SlideController
from namo_core.services.classroom.classroom_service import ClassroomService
from namo_core.services.classroom.slide_content_service import SlideContentService
from namo_core.database.core import get_db
from namo_core.database.models import EventLog
from namo_core.api.routes.reasoning import get_reasoner

router = APIRouter(prefix="/classroom", tags=["classroom"])


class SessionUpdate(BaseModel):
    mode: Optional[str] = None
    lesson: Optional[str] = None
    students_connected: Optional[int] = None
    projector: Optional[str] = None
    assistant_state: Optional[str] = None


class StartSessionRequest(BaseModel):
    lesson_id: str


class StudentRequest(BaseModel):
    name: str


# ------------------------------------------------------------------
# Session
# ------------------------------------------------------------------


@router.get("/session")
def classroom_session() -> dict:
    """Return the current classroom session state."""
    return ClassroomService().get_session_summary()


@router.patch("/session")
def update_classroom_session(payload: SessionUpdate) -> dict:
    """Update high-level session metadata. For slide/projector use specific endpoints."""
    return ClassroomService().update_session(payload.model_dump())


@router.post("/session/start")
def start_session(payload: StartSessionRequest) -> dict:
    """Start a classroom session for the given lesson.

    Loads slide count, resets to slide 1, sets projector to 'lesson' mode,
    and transitions assistant state to 'teaching'.
    """
    try:
        return ClassroomService().start_session(payload.lesson_id.strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/session/end")
def end_session() -> dict:
    """End the current classroom session.

    Clears student roster, sets projector to standby, resets assistant state.
    """
    return ClassroomService().end_session()


# ------------------------------------------------------------------
# Slides
# ------------------------------------------------------------------


@router.get("/slide")
def get_current_slide() -> dict:
    """Return current slide position."""
    return SlideController().current()


@router.get("/slide/content")
def get_slide_content() -> dict:
    """Return full content of the current slide (title, body, dhamma_point, etc.)."""
    return SlideController().content()


@router.post("/slide/next")
def next_slide() -> dict:
    """Advance to the next slide."""
    return SlideController().next_slide()


@router.post("/slide/prev")
def prev_slide() -> dict:
    """Go back one slide."""
    return SlideController().prev_slide()


@router.post("/slide/{slide_n}")
def go_to_slide(slide_n: int) -> dict:
    """Jump to a specific slide number."""
    try:
        return SlideController().go_to(slide_n)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ------------------------------------------------------------------
# Projector
# ------------------------------------------------------------------


@router.get("/projector")
def get_projector_status() -> dict:
    """Return current projector mode and valid modes."""
    return ProjectorController().status()


@router.post("/projector/{mode}")
def set_projector_mode(mode: str) -> dict:
    """Set the projector to a specific mode (off/lesson/quiz/reflection/standby)."""
    try:
        return ProjectorController().set_mode(mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ------------------------------------------------------------------
# Students
# ------------------------------------------------------------------


@router.post("/student/connect")
def connect_student(payload: StudentRequest) -> dict:
    """Register a student as connected to the current session."""
    try:
        return ClassroomService().connect_student(payload.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/student/disconnect")
def disconnect_student(payload: StudentRequest) -> dict:
    """Remove a student from the current session roster."""
    try:
        return ClassroomService().disconnect_student(payload.name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/students")
def get_students() -> dict:
    """Return the current student roster and total count."""
    return ClassroomService().get_students()


# ------------------------------------------------------------------
# Assistant state
# ------------------------------------------------------------------


@router.post("/assistant/{state}")
def transition_assistant_state(state: str) -> dict:
    """Transition the assistant state machine to the given state.

    Valid states: ready, teaching, listening, responding, paused, done.
    """
    try:
        return ClassroomService().transition_state(state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ------------------------------------------------------------------
# Events & Lessons
# ------------------------------------------------------------------


@router.get("/events")
def get_events(
    n: int = Query(
        default=20, ge=1, le=200, description="Number of recent events to return"
    ),
) -> dict:
    """Return the classroom event log (most recent N events)."""
    return ClassroomService().get_events(n)


@router.get("/lessons")
def list_lessons() -> dict:
    """Return all available lessons with slide count."""
    lessons = SlideContentService().list_lessons()
    return {"count": len(lessons), "lessons": lessons}


# ------------------------------------------------------------------
# Analytics (New Feature)
# ------------------------------------------------------------------


@router.post("/session/{session_id}/generate-summary")
def generate_session_summary(session_id: str, db: Session = Depends(get_db)) -> dict:
    """
    [New Feature] AI Session Analytics
    ประมวลผลข้อมูลตลอดคาบเรียน (ประวัติคำถาม, อารมณ์) เพื่อให้ AI สรุปเป็นรายงานสำหรับครู
    """
    events = db.query(EventLog).filter(EventLog.session_id == session_id).all()
    if not events:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูล EventLog สำหรับ Session นี้")

    transcript_data = []
    emotion_counts = {}

    for e in events:
        if (
            e.event_type in ["voice_pipeline", "text_pipeline", "classroom_loop"]
            and e.content
        ):
            transcript_data.append(f"Q: {e.content} -> A: {e.response}")
        if e.emotion_state:
            emotion_counts[e.emotion_state] = emotion_counts.get(e.emotion_state, 0) + 1

    prompt = (
        f"คุณคือผู้เชี่ยวชาญด้านการประเมินการสอน จงสรุปผลการเรียนการสอนจากข้อมูลต่อไปนี้:\n"
        f"สถิติอารมณ์ความสนใจของนักเรียน (จำนวนครั้ง): {emotion_counts}\n"
        f"ประวัติการถามตอบในห้องเรียน:\n"
        + "\n".join(transcript_data[-30:])
        + "\n\nให้สรุปสั้นๆ 3 หัวข้อ:\n1. ภาพรวมความสนใจ\n2. ประเด็นคำถามหลักที่นักเรียนสงสัย\n3. ข้อเสนอแนะสำหรับครูในคาบถัดไป"
    )

    ai_result = get_reasoner().explain(
        prompt, teaching_hint="วิเคราะห์อย่างเป็นกลาง ใช้ภาษาทางการและเข้าใจง่าย"
    )

    return {
        "session_id": session_id,
        "total_interactions": len(transcript_data),
        "emotion_stats": emotion_counts,
        "ai_summary": ai_result.get("answer", ""),
    }
