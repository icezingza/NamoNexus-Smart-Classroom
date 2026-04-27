import json
from pathlib import Path

class LessonRepository:
    def __init__(self):
        self.data_path = Path(__file__).parent / "lesson_plans.json"
        self._lessons = self._load()

    def _load(self):
        if not self.data_path.exists():
            return []
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def get(self, lesson_id: str):
        for lesson in self._lessons:
            if lesson.get("id") == lesson_id:
                return lesson
        return None

    def list_lessons(self):
        return self._lessons
