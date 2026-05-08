import json

import pytest
from fastapi.testclient import TestClient

from namo_core.api.app import app
from namo_core.config.settings import get_settings


def test_classroom_session_can_be_updated(auth_headers) -> None:
    """PATCH /classroom/session requires Bearer JWT — uses conftest auth_headers fixture."""
    settings = get_settings()
    state_path = settings.classroom_state_path
    original = json.loads(state_path.read_text(encoding="utf-8"))

    try:
        with TestClient(app, headers=auth_headers) as client:
            response = client.patch(
                "/classroom/session",
                json={
                    "mode": "guided",
                    "students_connected": 5,
                    "assistant_state": "explaining",
                },
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["mode"] == "guided"
        assert payload["students_connected"] == 5
        assert payload["assistant_state"] == "explaining"
    finally:
        state_path.write_text(
            json.dumps(original, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
        )
