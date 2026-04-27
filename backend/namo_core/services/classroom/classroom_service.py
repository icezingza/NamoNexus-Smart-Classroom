"""ClassroomService — Phase 6: Full classroom session management.

Orchestrates slide content, student tracking, event logging, and
assistant state machine for the classroom session lifecycle.

Singleton-style components (StudentTracker, EventLog, StateMachine)
are module-level so they persist across HTTP requests in the same process.
"""
from __future__ import annotations

from namo_core.config.settings import get_settings
from namo_core.services.classroom.classroom_event_log import ClassroomEventLog
from namo_core.services.classroom.session_store import ClassroomSessionStore
from namo_core.services.classroom.slide_content_service import SlideContentService
from namo_core.services.classroom.student_tracker import StudentTracker
from namo_core.services.classroom.teaching_state_machine import TeachingStateMachine

# Module-level singletons — persist for the lifetime of the server process
_student_tracker = StudentTracker()
_event_log = ClassroomEventLog()
_state_machine = TeachingStateMachine()
_slide_content = SlideContentService()


class ClassroomService:
    """Facade for all classroom session operations."""

    def __init__(self) -> None:
        settings = get_settings()
        self.store = ClassroomSessionStore(settings.classroom_state_path)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def get_session_summary(self) -> dict:
        """Return the current session state enriched with live data."""
        session = await self.store.load()
        session["students_connected"] = await _student_tracker.count()
        session["assistant_state"] = _state_machine.current
        session["allowed_transitions"] = _state_machine.allowed_transitions()
        return session

    async def update_session(self, payload: dict) -> dict:
        """Merge arbitrary session metadata updates.

        Skips None values. Coerces students_connected to non-negative int.
        Does NOT validate assistant_state transitions — use transition_state() instead.
        """
        session = await self.store.load()
        for key, value in payload.items():
            if value is None:
                continue
            session[key] = value
        session["students_connected"] = max(int(session.get("students_connected", 0)), 0)
        return await self.store.save(session)

    async def start_session(self, lesson_id: str) -> dict:
        """Start a new classroom session for the given lesson.

        - Loads slide count from SlideContentService
        - Resets slide position to 1
        - Sets projector mode to 'lesson'
        - Transitions assistant_state: any → teaching
        - Logs session_started event

        Args:
            lesson_id: Lesson id or title substring to load.

        Returns:
            Updated session state dict.

        Raises:
            ValueError: If lesson_id is not found in lesson plans.
        """
        total_slides = _slide_content.total_slides_for(lesson_id)
        if total_slides == 0:
            raise ValueError(f"Lesson '{lesson_id}' not found in lesson plans.")

        # Find the canonical lesson title for display
        matches = [l for l in _slide_content.list_lessons() if l["id"] == lesson_id]
        lesson_title = matches[0]["title"] if matches else lesson_id

        session = await self.store.load()
        session.update({
            "mode": "lesson",
            "lesson_id": lesson_id,
            "lesson": lesson_title,
            "current_slide": 1,
            "total_slides": total_slides,
            "projector": "lesson",
        })
        await self.store.save(session)

        # Transition state machine to teaching (force via reset then transition)
        _state_machine.reset()
        _state_machine.transition("teaching")

        await _event_log.log("session_started", {
            "lesson_id": lesson_id,
            "lesson": lesson_title,
            "total_slides": total_slides,
        })

        return await self.get_session_summary()

    async def end_session(self) -> dict:
        """End the current classroom session.

        - Clears student roster
        - Sets projector to standby
        - Transitions assistant_state → done → ready
        - Logs session_ended event
        """
        session = await self.store.load()
        session["projector"] = "standby"
        session["mode"] = "demo"
        await self.store.save(session)

        await _student_tracker.clear()

        # Transition to done then ready
        if _state_machine.current != "done":
            try:
                _state_machine.transition("done")
            except ValueError:
                _state_machine.reset()
        _state_machine.transition("ready") if _state_machine.current == "done" else None

        await _event_log.log("session_ended", {"lesson": session.get("lesson", "")})

        return await self.get_session_summary()

    # ------------------------------------------------------------------
    # Student management
    # ------------------------------------------------------------------

    async def connect_student(self, name: str) -> dict:
        """Register a student as connected to the session.

        Args:
            name: Student name.

        Returns:
            Student info dict plus updated session students_connected count.
        """
        result = await _student_tracker.connect(name)
        session = await self.store.load()
        session["students_connected"] = await _student_tracker.count()
        await self.store.save(session)
        await _event_log.log("student_joined", {"name": name})
        return result

    async def disconnect_student(self, name: str) -> dict:
        """Remove a student from the session roster.

        Args:
            name: Student name.

        Returns:
            Removal confirmation dict.

        Raises:
            ValueError: If student is not in roster.
        """
        result = await _student_tracker.disconnect(name)
        session = await self.store.load()
        session["students_connected"] = await _student_tracker.count()
        await self.store.save(session)
        await _event_log.log("student_left", {"name": name})
        return result

    async def get_students(self) -> dict:
        """Return current student roster and count."""
        return {
            "count": await _student_tracker.count(),
            "students": await _student_tracker.roster(),
        }

    # ------------------------------------------------------------------
    # Assistant state management
    # ------------------------------------------------------------------

    async def transition_state(self, target: str) -> dict:
        """Transition the assistant state machine to target.

        Args:
            target: Desired next state.

        Returns:
            Dict with previous, current, and allowed_transitions.

        Raises:
            ValueError: If transition is not allowed.
        """
        previous = _state_machine.current
        new_state = _state_machine.transition(target)

        session = await self.store.load()
        session["assistant_state"] = new_state
        await self.store.save(session)

        await _event_log.log("assistant_state_changed", {
            "from": previous,
            "to": new_state,
        })

        return {
            "previous_state": previous,
            "current_state": new_state,
            "allowed_transitions": _state_machine.allowed_transitions(),
        }

    # ------------------------------------------------------------------
    # Event log
    # ------------------------------------------------------------------

    async def get_events(self, n: int = 20) -> dict:
        """Return recent classroom events.

        Args:
            n: Maximum number of events to return (default 20).

        Returns:
            Dict with total count and list of recent events.
        """
        return {
            "total": await _event_log.count(),
            "events": await _event_log.recent(n),
        }


# ---------------------------------------------------------------------------
# Module-level helper for WebSocket route (Phase 10)
# ---------------------------------------------------------------------------

async def get_classroom_state() -> dict:
    """Return a lightweight classroom state snapshot for WebSocket broadcast.

    ใช้ module-level singletons โดยตรง เพื่อไม่ต้อง instantiate ClassroomService
    (ซึ่งต้องการ settings + disk I/O) ทุกครั้งที่ push state ทุก 5 วินาที

    Returns:
        Dict with assistant_state, projector, students_connected, allowed_transitions.
    """
    from namo_core.services.classroom.session_store import ClassroomSessionStore
    from namo_core.config.settings import get_settings

    try:
        store = ClassroomSessionStore(get_settings().classroom_state_path)
        session = await store.load()
    except Exception:
        session = {}

    return {
        "assistant_state": _state_machine.current,
        "allowed_transitions": _state_machine.allowed_transitions(),
        "projector": session.get("projector", "standby"),
        "students_connected": await _student_tracker.count(),
        "mode": session.get("mode", "demo"),
        "lesson": session.get("lesson", ""),
        "current_slide": session.get("current_slide", 1),
        "total_slides": session.get("total_slides", 0),
    }
