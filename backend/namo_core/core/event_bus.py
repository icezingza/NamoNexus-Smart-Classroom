class EventBus:
    """Small in-memory event collector for demo orchestration flows."""

    def __init__(self) -> None:
        self._events: list[dict] = []

    def publish(self, event_type: str, payload: dict) -> None:
        self._events.append({"type": event_type, "payload": payload})

    def snapshot(self) -> list[dict]:
        return list(self._events)
