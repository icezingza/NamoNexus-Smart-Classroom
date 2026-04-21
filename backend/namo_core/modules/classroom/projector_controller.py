"""ProjectorController — manages the projector mode in the classroom session.

Valid modes:
  off        — projector is off
  lesson     — displaying lesson slides
  quiz       — quiz mode (whiteboard / question display)
  reflection — mindfulness reflection / silent pause

Mode is persisted in classroom_state.json as the "projector" field.
"""
from __future__ import annotations

from namo_core.config.settings import get_settings
from namo_core.services.classroom.session_store import ClassroomSessionStore

VALID_MODES = {"off", "lesson", "quiz", "reflection", "standby"}


class ProjectorController:
    """Controls projector display mode in the classroom."""

    def __init__(self) -> None:
        settings = get_settings()
        self._store = ClassroomSessionStore(settings.classroom_state_path)

    def status(self) -> dict:
        """Return current projector mode."""
        session = self._store.load()
        return {"mode": session.get("projector", "standby"), "valid_modes": sorted(VALID_MODES)}

    def set_mode(self, mode: str) -> dict:
        """Switch projector to the given mode.

        Raises ``ValueError`` when mode is not recognised.
        """
        mode = mode.lower()
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid projector mode '{mode}'. Valid: {sorted(VALID_MODES)}")
        session = self._store.load()
        session["projector"] = mode
        self._store.save(session)
        return {"mode": mode, "changed": True}

    def toggle_off(self) -> dict:
        """Convenience: turn projector off."""
        return self.set_mode("off")
