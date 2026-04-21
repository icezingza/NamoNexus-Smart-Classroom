"""ClassroomEventLog — Phase 6: Append-only event log for classroom sessions.

Records significant events during a classroom session so the dashboard,
teacher, and debugging tools can see a timeline of what happened.

Events are stored in-memory (deque) and reset when the session ends
or the server restarts. Capacity is capped at 200 events.

Event types:
    session_started       – new session began
    session_ended         – session ended
    slide_changed         – projector slide changed
    projector_changed     – projector mode changed
    student_joined        – student connected to session
    student_left          – student disconnected
    assistant_state_changed – assistant state transitioned
    teaching_hint_applied – emotion-driven teaching hint was used
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone

_MAX_EVENTS = 200


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class ClassroomEventLog:
    """Append-only event log with a fixed-size rolling window."""

    def __init__(self, capacity: int = _MAX_EVENTS) -> None:
        self._events: deque[dict] = deque(maxlen=capacity)

    def log(self, event_type: str, data: dict | None = None) -> dict:
        """Append a new event to the log.

        Args:
            event_type: One of the defined event type strings.
            data: Optional dict of event-specific data.

        Returns:
            The recorded event dict.
        """
        event: dict = {
            "timestamp": _now_iso(),
            "type": event_type,
            "data": data or {},
        }
        self._events.append(event)
        return event

    def recent(self, n: int = 20) -> list[dict]:
        """Return the N most recent events (newest last).

        Args:
            n: Maximum number of events to return.

        Returns:
            List of event dicts.
        """
        events = list(self._events)
        return events[-n:] if n < len(events) else events

    def all(self) -> list[dict]:
        """Return all stored events (oldest first)."""
        return list(self._events)

    def count(self) -> int:
        """Return total number of events logged."""
        return len(self._events)

    def clear(self) -> None:
        """Remove all events (called on session reset)."""
        self._events.clear()

    def since(self, event_type: str) -> list[dict]:
        """Return all events of a given type."""
        return [e for e in self._events if e["type"] == event_type]
