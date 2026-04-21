"""TeachingStateMachine — Phase 6: Valid state transitions for assistant_state.

Prevents the classroom assistant from jumping to nonsensical states.
Every transition must follow a defined path.

State diagram:
    ready ──────────────────────────────────────── (initial)
      │
      ▼ start_session()
    teaching ◄──────────────────────────────────── (default active state)
      │        ▲
      │ (student speaks)
      ▼        │
    listening  │ (answer delivered)
      │        │
      ▼        │
    responding ─────────────────────────────────►
      │
      │ (projector off / break)
    teaching ──► paused ──► teaching (resume)
      │
      ▼ end_session()
    done ──────► ready (reset)

Any state can transition to 'ready' (emergency reset).
"""
from __future__ import annotations

# Map current_state → set of allowed next states
_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "ready":      frozenset({"teaching"}),
    "teaching":   frozenset({"listening", "paused", "done"}),
    "listening":  frozenset({"responding", "teaching"}),
    "responding": frozenset({"teaching"}),
    "paused":     frozenset({"teaching", "done"}),
    "done":       frozenset({"ready"}),
}

# Reset to 'ready' is always allowed regardless of current state
_RESET_STATE = "ready"

ALL_STATES: frozenset[str] = frozenset(_VALID_TRANSITIONS.keys())


class TeachingStateMachine:
    """Controls valid assistant_state transitions for the classroom pipeline.

    Args:
        initial_state: Starting state (default 'ready').
    """

    def __init__(self, initial_state: str = "ready") -> None:
        if initial_state not in ALL_STATES:
            raise ValueError(
                f"Invalid initial_state '{initial_state}'. "
                f"Must be one of: {sorted(ALL_STATES)}"
            )
        self._state = initial_state

    @property
    def current(self) -> str:
        """The current assistant state."""
        return self._state

    def can_transition(self, target: str) -> bool:
        """Check if transition to target state is allowed.

        Args:
            target: The desired next state.

        Returns:
            True if the transition is valid from the current state.
        """
        if target == _RESET_STATE:
            return True
        return target in _VALID_TRANSITIONS.get(self._state, frozenset())

    def transition(self, target: str) -> str:
        """Transition to target state.

        Args:
            target: The desired next state.

        Returns:
            The new current state.

        Raises:
            ValueError: If transition is not allowed from the current state.
        """
        if not self.can_transition(target):
            allowed = sorted(_VALID_TRANSITIONS.get(self._state, frozenset()) | {_RESET_STATE})
            raise ValueError(
                f"Cannot transition from '{self._state}' to '{target}'. "
                f"Allowed: {allowed}"
            )
        self._state = target
        return self._state

    def allowed_transitions(self) -> list[str]:
        """Return sorted list of valid next states from the current state."""
        base = _VALID_TRANSITIONS.get(self._state, frozenset())
        # Always include 'ready' as a reset option (unless already there)
        if self._state != _RESET_STATE:
            base = base | {_RESET_STATE}
        return sorted(base)

    def reset(self) -> str:
        """Force-reset to 'ready' regardless of current state."""
        self._state = _RESET_STATE
        return self._state
