import json
from pathlib import Path


DEFAULT_SESSION_STATE = {
    "mode": "demo",
    "lesson": "Introduction to Buddhism",
    "students_connected": 0,
    "projector": "standby",
    "assistant_state": "ready",
}


class ClassroomSessionStore:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def load(self) -> dict:
        self._ensure_exists()
        return json.loads(self.file_path.read_text(encoding="utf-8"))

    def save(self, payload: dict) -> dict:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return payload

    def _ensure_exists(self) -> None:
        if self.file_path.exists():
            return
        self.save(dict(DEFAULT_SESSION_STATE))
