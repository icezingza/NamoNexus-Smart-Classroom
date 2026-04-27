"""StudentTracker — Phase 6: In-memory student roster for classroom sessions.

Tracks which students are currently connected to the classroom session.
State is in-memory only; it resets when the server restarts.
This is intentional: student presence is transient per-session data.

Concurrent access is not a concern in single-process deployment.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
import redis.asyncio as redis

from namo_core.config.settings import get_settings

logger = logging.getLogger(__name__)
REDIS_KEY_ROSTER = "namo:classroom:roster"

def _hash_pii(name: str) -> str:
    """Enterprise Infrastructure Security: Hash PII to enforce Data Residency rules."""
    return hashlib.sha256(name.encode("utf-8")).hexdigest()

class StudentTracker:
    """Manages the set of students connected to the current classroom session."""

    def __init__(self) -> None:
        settings = get_settings()
        if settings.redis_url:
            self.redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            self.use_redis = True
        else:
            self.use_redis = False
            self._roster: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def connect(self, name: str) -> dict:
        """Register a student as connected.

        If the student is already in the roster, updates their join time.

        Args:
            name: Student name or identifier (stripped of whitespace).

        Returns:
            dict with student name, joined_at, and total count.

        Raises:
            ValueError: If name is empty after stripping.
        """
        name = name.strip()
        if not name:
            raise ValueError("Student name must not be empty.")
        
        hashed_name = _hash_pii(name)
        joined_at = datetime.now(tz=timezone.utc).isoformat()
        
        if self.use_redis:
            await self.redis.hset(REDIS_KEY_ROSTER, hashed_name, joined_at)
            total = await self.redis.hlen(REDIS_KEY_ROSTER)
        else:
            self._roster[hashed_name] = joined_at
            total = len(self._roster)
            
        return {"name": hashed_name, "joined_at": joined_at, "total_connected": total}

    async def disconnect(self, name: str) -> dict:
        """Remove a student from the roster.

        Args:
            name: Student name to remove.

        Returns:
            dict with removed name and remaining count.

        Raises:
            ValueError: If student is not in roster.
        """
        name = name.strip()
        hashed_name = _hash_pii(name)
        
        if self.use_redis:
            exists = await self.redis.hexists(REDIS_KEY_ROSTER, hashed_name)
            if not exists:
                raise ValueError(f"Student '{name}' is not in the current roster.")
            await self.redis.hdel(REDIS_KEY_ROSTER, hashed_name)
            total = await self.redis.hlen(REDIS_KEY_ROSTER)
        else:
            if hashed_name not in self._roster:
                raise ValueError(f"Student '{name}' is not in the current roster.")
            self._roster.pop(hashed_name)
            total = len(self._roster)
            
        return {"name": hashed_name, "removed": True, "total_connected": total}

    async def roster(self) -> list[dict]:
        """Return the current student roster sorted by join time.

        Returns:
            List of dicts with name and joined_at for each connected student.
        """
        if self.use_redis:
            data = await self.redis.hgetall(REDIS_KEY_ROSTER)
        else:
            data = self._roster
            
        return sorted(
            [{"name": hashed_n, "joined_at": ts} for hashed_n, ts in data.items()],
            key=lambda s: s["joined_at"],
        )

    async def count(self) -> int:
        """Return the number of currently connected students."""
        if self.use_redis:
            return await self.redis.hlen(REDIS_KEY_ROSTER)
        return len(self._roster)

    async def clear(self) -> None:
        """Remove all students from the roster (called on session end)."""
        if self.use_redis:
            await self.redis.delete(REDIS_KEY_ROSTER)
        else:
            self._roster.clear()

    async def is_connected(self, name: str) -> bool:
        """Check if a student is currently connected."""
        hashed_name = _hash_pii(name.strip())
        if self.use_redis:
            return await self.redis.hexists(REDIS_KEY_ROSTER, hashed_name)
        return hashed_name in self._roster
