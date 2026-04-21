"""Integration tests for Phase 6 Classroom System.

Tests the new classroom API endpoints end-to-end via FastAPI TestClient.
"""
import pytest
from fastapi.testclient import TestClient

from namo_core.api.app import app

client = TestClient(app)


# ------------------------------------------------------------------
# Available Lessons
# ------------------------------------------------------------------

class TestLessonsEndpoint:
    def test_list_lessons_returns_200(self):
        response = client.get("/classroom/lessons")
        assert response.status_code == 200

    def test_list_lessons_has_count_and_list(self):
        data = client.get("/classroom/lessons").json()
        assert "count" in data
        assert "lessons" in data
        assert data["count"] == len(data["lessons"])

    def test_each_lesson_has_required_keys(self):
        data = client.get("/classroom/lessons").json()
        for lesson in data["lessons"]:
            assert "id" in lesson
            assert "title" in lesson
            assert "total_slides" in lesson
            assert lesson["total_slides"] > 0


# ------------------------------------------------------------------
# Session Start / End
# ------------------------------------------------------------------

class TestSessionLifecycle:
    LESSON_ID = "lesson-intro-buddhism"

    def test_start_session_returns_200(self):
        response = client.post("/classroom/session/start", json={"lesson_id": self.LESSON_ID})
        assert response.status_code == 200

    def test_start_session_sets_lesson(self):
        data = client.post("/classroom/session/start", json={"lesson_id": self.LESSON_ID}).json()
        assert data.get("lesson_id") == self.LESSON_ID
        assert data.get("mode") == "lesson"
        assert data.get("projector") == "lesson"
        assert data.get("assistant_state") == "teaching"

    def test_start_session_resets_slide_to_1(self):
        data = client.post("/classroom/session/start", json={"lesson_id": self.LESSON_ID}).json()
        # Slide resets via session store; verify via /classroom/slide
        slide = client.get("/classroom/slide").json()
        assert slide["current_slide"] == 1

    def test_start_session_sets_total_slides(self):
        client.post("/classroom/session/start", json={"lesson_id": self.LESSON_ID})
        slide = client.get("/classroom/slide").json()
        # lesson-intro-buddhism has 4 objectives → 6 slides (intro + 4 + summary)
        assert slide["total_slides"] == 6

    def test_start_session_invalid_lesson_returns_400(self):
        response = client.post("/classroom/session/start", json={"lesson_id": "does-not-exist"})
        assert response.status_code == 400

    def test_end_session_returns_200(self):
        client.post("/classroom/session/start", json={"lesson_id": self.LESSON_ID})
        response = client.post("/classroom/session/end")
        assert response.status_code == 200

    def test_end_session_sets_standby(self):
        client.post("/classroom/session/start", json={"lesson_id": self.LESSON_ID})
        data = client.post("/classroom/session/end").json()
        assert data.get("projector") == "standby"
        assert data.get("mode") == "demo"


# ------------------------------------------------------------------
# Slide Content
# ------------------------------------------------------------------

class TestSlideContent:
    def setup_method(self):
        client.post("/classroom/session/start", json={"lesson_id": "lesson-intro-buddhism"})

    def test_get_slide_content_returns_200(self):
        response = client.get("/classroom/slide/content")
        assert response.status_code == 200

    def test_slide_content_has_required_fields(self):
        data = client.get("/classroom/slide/content").json()
        for key in ("slide_number", "total_slides", "lesson_id", "title", "body",
                    "dhamma_point", "key_concept", "teaching_note"):
            assert key in data, f"Missing key: {key}"

    def test_slide_1_is_intro(self):
        data = client.get("/classroom/slide/content").json()
        assert data["slide_number"] == 1
        assert data["key_concept"] == "introduction"

    def test_next_slide_changes_content(self):
        slide1_title = client.get("/classroom/slide/content").json()["title"]
        client.post("/classroom/slide/next")
        slide2_title = client.get("/classroom/slide/content").json()["title"]
        assert slide2_title != slide1_title

    def test_last_slide_is_summary(self):
        # Jump to last slide
        total = client.get("/classroom/slide").json()["total_slides"]
        client.post(f"/classroom/slide/{total}")
        data = client.get("/classroom/slide/content").json()
        assert data["key_concept"] == "summary"


# ------------------------------------------------------------------
# Student Tracking
# ------------------------------------------------------------------

class TestStudentTracking:
    def setup_method(self):
        # End session to reset student tracker
        client.post("/classroom/session/end")

    def test_connect_student_returns_200(self):
        response = client.post("/classroom/student/connect", json={"name": "Namo"})
        assert response.status_code == 200

    def test_connect_returns_name_and_count(self):
        data = client.post("/classroom/student/connect", json={"name": "Ariya"}).json()
        assert data["name"] == "Ariya"
        assert "joined_at" in data
        assert data["total_connected"] >= 1

    def test_get_students_shows_roster(self):
        client.post("/classroom/student/connect", json={"name": "Sati"})
        data = client.get("/classroom/students").json()
        assert "count" in data
        assert "students" in data
        names = [s["name"] for s in data["students"]]
        assert "Sati" in names

    def test_disconnect_removes_student(self):
        client.post("/classroom/student/connect", json={"name": "Panna"})
        resp = client.post("/classroom/student/disconnect", json={"name": "Panna"})
        assert resp.status_code == 200
        assert resp.json()["removed"] is True

    def test_disconnect_unknown_student_returns_404(self):
        response = client.post("/classroom/student/disconnect", json={"name": "DoesNotExist"})
        assert response.status_code == 404

    def test_empty_name_returns_400(self):
        response = client.post("/classroom/student/connect", json={"name": "   "})
        assert response.status_code == 400


# ------------------------------------------------------------------
# Teaching State Machine
# ------------------------------------------------------------------

class TestAssistantState:
    def test_transition_to_teaching_after_start(self):
        client.post("/classroom/session/start", json={"lesson_id": "lesson-intro-buddhism"})
        session = client.get("/classroom/session").json()
        assert session["assistant_state"] == "teaching"

    def test_valid_transition_returns_200(self):
        client.post("/classroom/session/start", json={"lesson_id": "lesson-intro-buddhism"})
        response = client.post("/classroom/assistant/listening")
        assert response.status_code == 200

    def test_transition_response_has_states(self):
        client.post("/classroom/session/start", json={"lesson_id": "lesson-intro-buddhism"})
        data = client.post("/classroom/assistant/listening").json()
        assert data["previous_state"] == "teaching"
        assert data["current_state"] == "listening"
        assert "allowed_transitions" in data

    def test_invalid_transition_returns_400(self):
        client.post("/classroom/session/start", json={"lesson_id": "lesson-intro-buddhism"})
        # teaching → done is NOT valid; done requires teaching→paused→done or teaching→done
        # Actually teaching → done IS valid per the state machine
        # Let's test teaching → responding (which is not valid)
        response = client.post("/classroom/assistant/responding")
        assert response.status_code == 400

    def test_reset_to_ready_always_allowed(self):
        client.post("/classroom/session/start", json={"lesson_id": "lesson-intro-buddhism"})
        response = client.post("/classroom/assistant/ready")
        assert response.status_code == 200
        assert response.json()["current_state"] == "ready"


# ------------------------------------------------------------------
# Event Log
# ------------------------------------------------------------------

class TestEventLog:
    def test_get_events_returns_200(self):
        response = client.get("/classroom/events")
        assert response.status_code == 200

    def test_events_has_total_and_list(self):
        data = client.get("/classroom/events").json()
        assert "total" in data
        assert "events" in data

    def test_start_session_creates_event(self):
        client.post("/classroom/session/start", json={"lesson_id": "lesson-mindfulness"})
        data = client.get("/classroom/events").json()
        types = [e["type"] for e in data["events"]]
        assert "session_started" in types

    def test_student_join_creates_event(self):
        client.post("/classroom/student/connect", json={"name": "EventTest"})
        data = client.get("/classroom/events").json()
        types = [e["type"] for e in data["events"]]
        assert "student_joined" in types

    def test_n_param_limits_results(self):
        for i in range(5):
            client.post("/classroom/session/start", json={"lesson_id": "lesson-intro-buddhism"})
        data = client.get("/classroom/events?n=2").json()
        assert len(data["events"]) <= 2
