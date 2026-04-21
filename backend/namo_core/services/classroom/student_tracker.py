"""StudentTracker — Phase 6: In-memory student roster for classroom sessions.

Tracks which students are currently connected to the classroom session.
State is in-memory only; it resets when the server restarts.
This is intentional: student presence is transient per-session data.

Concurrent access is not a concern in single-process deployment.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

def _hash_pii(name: str) -> str:
    """Enterprise Infrastructure Security: Hash PII to enforce Data Residency rules."""
    return hashlib.sha256(name.encode("utf-8")).hexdigest()

class StudentTracker:
    """Manages the set of students connected to the current classroom session."""

    def __init__(self) -> None:
        # name → ISO-format join timestamp
        self._roster: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect(self, name: str) -> dict:
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
        self._roster[hashed_name] = joined_at
        return {"name": hashed_name, "joined_at": joined_at, "total_connected": len(self._roster)}

    def disconnect(self, name: str) -> dict:
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
        if hashed_name not in self._roster:
            raise ValueError(f"Student '{name}' is not in the current roster.")
        self._roster.pop(hashed_name)
        return {"name": hashed_name, "removed": True, "total_connected": len(self._roster)}

    def roster(self) -> list[dict]:
        """Return the current student roster sorted by join time.

        Returns:
            List of dicts with name and joined_at for each connected student.
        """
        return sorted(
            [{"name": hashed_n, "joined_at": ts} for hashed_n, ts in self._roster.items()],
            key=lambda s: s["joined_at"],
        )

    def count(self) -> int:
        """Return the number of currently connected students."""
        return len(self._roster)

    def clear(self) -> None:
        """Remove all students from the roster (called on session end)."""
        self._roster.clear()

    def is_connected(self, name: str) -> bool:
        """Check if a student is currently connected."""
        return _hash_pii(name.strip()) in self._roster
