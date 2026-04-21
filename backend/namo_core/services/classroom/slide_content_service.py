"""SlideContentService — Phase 6: Lesson-to-slide content generator.

Converts a lesson plan entry into a sequence of structured slide objects
for display on the classroom projector.

Slide layout for a lesson with N objectives:
    Slide 1           — Introduction / title slide
    Slides 2 … N+1   — One slide per learning objective
    Slide N+2         — Summary / reflection slide

Each slide contains:
    slide_number    – 1-indexed position
    total_slides    – total count for this lesson
    lesson_id       – source lesson identifier
    lesson_title    – human-readable lesson name
    title           – slide heading
    body            – main explanatory text (Thai + English)
    dhamma_point    – core Dhamma teaching distilled to one sentence
    key_concept     – primary concept tag for this slide
    teaching_note   – tip for the teacher / assistant voice
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


def _lesson_data_path() -> Path:
    """Return path to lesson_plans.json relative to this file.

    File layout:
        namo_core/services/classroom/slide_content_service.py  ← __file__
        namo_core/knowledge/lessons/lesson_plans.json          ← target
    parents[2] = namo_core/
    """
    return Path(__file__).resolve().parents[2] / "knowledge" / "lessons" / "lesson_plans.json"


@lru_cache(maxsize=1)
def _load_lessons() -> list[dict]:
    """Load and cache lesson plans from JSON file."""
    path = _lesson_data_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _find_lesson(lesson_id: str) -> dict | None:
    """Find a lesson by id; also accepts title substring match."""
    lessons = _load_lessons()
    for lesson in lessons:
        if lesson.get("id") == lesson_id:
            return lesson
    # Fallback: title substring match (case-insensitive)
    for lesson in lessons:
        if lesson_id.lower() in lesson.get("title", "").lower():
            return lesson
    return None


def _build_intro_slide(lesson: dict, total: int) -> dict:
    title = lesson.get("title", "")
    duration = lesson.get("duration_minutes", 60)
    level = lesson.get("level", "beginner")
    concepts = ", ".join(lesson.get("key_concepts", [])[:3])
    return {
        "slide_number": 1,
        "total_slides": total,
        "lesson_id": lesson.get("id", ""),
        "lesson_title": title,
        "title": title,
        "body": (
            f"ระดับ: {level} | เวลา: {duration} นาที\n"
            f"แนวคิดหลัก: {concepts}\n\n"
            "ยินดีต้อนรับสู่บทเรียนนี้ เราจะศึกษาธรรมะร่วมกันด้วยความตั้งใจและเปิดใจ"
        ),
        "dhamma_point": "การเริ่มต้นด้วยใจเปิดกว้างคือก้าวแรกของปัญญา",
        "key_concept": "introduction",
        "teaching_note": "เปิดด้วยคำถามกระตุ้นความสนใจ เช่น 'เคยได้ยินเรื่องนี้บ้างไหม?'",
    }


def _build_objective_slide(
    lesson: dict, objective: str, idx: int, slide_number: int, total: int
) -> dict:
    concepts = lesson.get("key_concepts", [])
    concept = concepts[idx] if idx < len(concepts) else concepts[0] if concepts else ""
    return {
        "slide_number": slide_number,
        "total_slides": total,
        "lesson_id": lesson.get("id", ""),
        "lesson_title": lesson.get("title", ""),
        "title": f"จุดประสงค์ที่ {idx + 1}: {concept}",
        "body": objective,
        "dhamma_point": f"ศึกษา {concept} เพื่อทำความเข้าใจธรรมชาติของจิต",
        "key_concept": concept,
        "teaching_note": (
            "ถามนักเรียนว่าเข้าใจคำนี้แล้วหรือยัง "
            "ใช้อุปมาจากชีวิตประจำวันเพื่อช่วยอธิบาย"
        ),
    }


def _build_summary_slide(lesson: dict, slide_number: int, total: int) -> dict:
    objectives = lesson.get("objectives", [])
    suttas = ", ".join(lesson.get("related_suttas", []))
    key_points = "\n".join(f"• {obj[:80]}" for obj in objectives[:4])
    return {
        "slide_number": slide_number,
        "total_slides": total,
        "lesson_id": lesson.get("id", ""),
        "lesson_title": lesson.get("title", ""),
        "title": "สรุปและทบทวน",
        "body": f"สิ่งที่เราได้เรียนรู้วันนี้:\n{key_points}\n\nพระสูตรที่เกี่ยวข้อง: {suttas}",
        "dhamma_point": "ความเข้าใจที่แท้จริงเกิดจากการนำไปปฏิบัติในชีวิตประจำวัน",
        "key_concept": "summary",
        "teaching_note": (
            "เปิดโอกาสให้นักเรียนถามคำถาม "
            "ทบทวนจุดสำคัญ 2-3 ข้อก่อนปิดบทเรียน"
        ),
    }


class SlideContentService:
    """Generates structured slide content from lesson plan data.

    Slide sequence: intro → one slide per objective → summary.
    Returns a list of slide dicts (1-indexed).
    """

    def slides_for_lesson(self, lesson_id: str) -> list[dict]:
        """Build all slides for a lesson.

        Args:
            lesson_id: Lesson id or title substring.

        Returns:
            Ordered list of slide dicts, or empty list if lesson not found.
        """
        lesson = _find_lesson(lesson_id)
        if not lesson:
            return []

        objectives: list[str] = lesson.get("objectives", [])
        total = len(objectives) + 2  # intro + N objectives + summary

        slides: list[dict] = [_build_intro_slide(lesson, total)]

        for idx, objective in enumerate(objectives):
            slides.append(
                _build_objective_slide(lesson, objective, idx, idx + 2, total)
            )

        slides.append(_build_summary_slide(lesson, total, total))
        return slides

    def slide_at(self, lesson_id: str, slide_number: int) -> dict | None:
        """Return a specific slide by number (1-indexed).

        Args:
            lesson_id: Lesson id or title substring.
            slide_number: 1-indexed slide number.

        Returns:
            Slide dict, or None if out of range or lesson not found.
        """
        slides = self.slides_for_lesson(lesson_id)
        if not slides:
            return None
        if slide_number < 1 or slide_number > len(slides):
            return None
        return slides[slide_number - 1]

    def total_slides_for(self, lesson_id: str) -> int:
        """Return total slide count for a lesson (0 if not found)."""
        slides = self.slides_for_lesson(lesson_id)
        return len(slides)

    def list_lessons(self) -> list[dict]:
        """Return all available lesson summaries."""
        return [
            {
                "id": l.get("id"),
                "title": l.get("title"),
                "level": l.get("level"),
                "duration_minutes": l.get("duration_minutes"),
                "total_slides": len(l.get("objectives", [])) + 2,
            }
            for l in _load_lessons()
        ]
