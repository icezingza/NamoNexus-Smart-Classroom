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

import json
import logging
from collections import deque
from datetime import datetime, timezone
import redis.asyncio as redis

from namo_core.config.settings import get_settings

logger = logging.getLogger(__name__)

_MAX_EVENTS = 200
REDIS_KEY_EVENTS = "namo:classroom:events"

def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()

class ClassroomEventLog:
    """Append-only event log with a fixed-size rolling window."""

    def __init__(self, capacity: int = _MAX_EVENTS) -> None:
        self.capacity = capacity
        settings = get_settings()
        if settings.redis_url:
            self.redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            self.use_redis = True
        else:
            self.use_redis = False
            self._events: deque[dict] = deque(maxlen=capacity)

    async def log(self, event_type: str, data: dict | None = None) -> dict:
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
        if self.use_redis:
            # RPUSH to append to the right
            await self.redis.rpush(REDIS_KEY_EVENTS, json.dumps(event, ensure_ascii=False))
            # Keep only the last capacity elements
            await self.redis.ltrim(REDIS_KEY_EVENTS, -self.capacity, -1)
        else:
            self._events.append(event)
        return event

    async def recent(self, n: int = 20) -> list[dict]:
        """Return the N most recent events (newest last)."""
        if self.use_redis:
            raw_events = await self.redis.lrange(REDIS_KEY_EVENTS, -n, -1)
            return [json.loads(e) for e in raw_events]
        else:
            events = list(self._events)
            return events[-n:] if n < len(events) else events

    async def all(self) -> list[dict]:
        """Return all stored events (oldest first)."""
        if self.use_redis:
            raw_events = await self.redis.lrange(REDIS_KEY_EVENTS, 0, -1)
            return [json.loads(e) for e in raw_events]
        return list(self._events)

    async def count(self) -> int:
        """Return total number of events logged."""
        if self.use_redis:
            return await self.redis.llen(REDIS_KEY_EVENTS)
        return len(self._events)

    async def clear(self) -> None:
        """Remove all events (called on session reset)."""
        if self.use_redis:
            await self.redis.delete(REDIS_KEY_EVENTS)
        else:
            self._events.clear()

    async def since(self, event_type: str) -> list[dict]:
        """Return all events of a given type."""
        all_events = await self.all()
        return [e for e in all_events if e["type"] == event_type]
