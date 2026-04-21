from namo_core.knowledge.lessons.repository import LessonRepository


class LessonGenerator:
    def __init__(self) -> None:
        self.repository = LessonRepository()

    def generate_outline(self, lesson_id: str) -> dict:
        lesson = self.repository.get(lesson_id) or self.repository.list_lessons()[0]
        return {
            "lesson_id": lesson["id"],
            "title": lesson["title"],
            "steps": [
                "Open with a short question to assess prior knowledge.",
                "Explain the concept in everyday classroom language.",
                "Close with a mindfulness reflection exercise.",
            ],
            "objectives": lesson["objectives"],
        }
