from fastapi import APIRouter, Query

from namo_core.services.lessons.generator import LessonGenerator

router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.get("/outline")
def lesson_outline(lesson_id: str = Query("lesson-intro-buddhism")) -> dict:
    return LessonGenerator().generate_outline(lesson_id)
