"""SlideController — manages lesson slide state in the classroom session.

Slide position is persisted in classroom_state.json (managed by ClassroomSessionStore).
Slides are 1-indexed. Total slides is determined by the lesson loaded via
SlideContentService when a session starts, or defaults to 10.

Phase 6 addition: content() method returns the actual slide content
(title, body, dhamma_point, key_concept, teaching_note) for the current slide.
"""
from __future__ import annotations

from namo_core.config.settings import get_settings
from namo_core.services.classroom.session_store import ClassroomSessionStore


class SlideController:
    """Controls classroom lesson slide progression."""

    def __init__(self) -> None:
        settings = get_settings()
        self._store = ClassroomSessionStore(settings.classroom_state_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def current(self) -> dict:
        """Return the current slide position info."""
        session = self._store.load()
        return self._slide_info(session)

    def content(self) -> dict:
        """Return the current slide's full content from SlideContentService.

        Looks up the lesson_id stored in the session and fetches the slide
        at current_slide position. Falls back to position info if no content
        is available (e.g. lesson not found in lesson plans).

        Returns:
            Slide content dict, or position-only dict if content unavailable.
        """
        from namo_core.services.classroom.slide_content_service import SlideContentService

        session = self._store.load()
        lesson_id: str = session.get("lesson_id") or session.get("lesson", "")
        current = session.get("current_slide", 1)

        if lesson_id:
            slide = SlideContentService().slide_at(lesson_id, current)
            if slide:
                return slide

        # Fallback: return position info only
        return {
            **self._slide_info(session),
            "title": session.get("lesson", "Lesson"),
            "body": "",
            "dhamma_point": "",
            "key_concept": "",
            "teaching_note": "",
        }

    def next_slide(self) -> dict:
        """Advance to the next slide (clamped at total_slides)."""
        session = self._store.load()
        total = session.get("total_slides", 10)
        current = session.get("current_slide", 1)
        session["current_slide"] = min(current + 1, total)
        self._store.save(session)
        return self._slide_info(session)

    def prev_slide(self) -> dict:
        """Go back one slide (clamped at 1)."""
        session = self._store.load()
        current = session.get("current_slide", 1)
        session["current_slide"] = max(current - 1, 1)
        self._store.save(session)
        return self._slide_info(session)

    def go_to(self, slide_n: int) -> dict:
        """Jump to a specific slide number (1-indexed)."""
        session = self._store.load()
        total = session.get("total_slides", 10)
        if not (1 <= slide_n <= total):
            raise ValueError(f"Slide {slide_n} out of range 1\u2013{total}")
        session["current_slide"] = slide_n
        self._store.save(session)
        return self._slide_info(session)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    @staticmethod
    def _slide_info(session: dict) -> dict:
        current = session.get("current_slide", 1)
        total = session.get("total_slides", 10)
        return {
            "current_slide": current,
            "total_slides": total,
            "progress_pct": round(current / total * 100) if total > 0 else 0,
            "lesson": session.get("lesson", ""),
            "lesson_id": session.get("lesson_id", ""),
        }
