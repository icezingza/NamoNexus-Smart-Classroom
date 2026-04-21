"""API contract tests for POST /reasoning/explain?speak=true — auto-TTS."""
from fastapi.testclient import TestClient

from namo_core.api.app import app

client = TestClient(app)


def test_reasoning_explain_without_speak_has_no_tts_key() -> None:
    response = client.post("/reasoning/explain", json={"query": "What is mindfulness?"})
    assert response.status_code == 200
    payload = response.json()
    # speak=false (default) — no tts key in response
    assert "tts" not in payload


def test_reasoning_explain_with_speak_true_includes_tts() -> None:
    response = client.post(
        "/reasoning/explain?speak=true",
        json={"query": "Explain the Four Noble Truths."},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "answer" in payload
    assert "tts" in payload, "speak=true should add 'tts' key to response"
    tts = payload["tts"]
    assert "provider" in tts
    assert "chars_synthesized" in tts
    assert "voice" in tts


def test_reasoning_explain_tts_chars_match_answer_length() -> None:
    response = client.post(
        "/reasoning/explain?speak=true",
        json={"query": "What is nibbana?"},
    )
    assert response.status_code == 200
    payload = response.json()
    answer = payload.get("answer", "")
    tts = payload.get("tts", {})
    if answer:
        assert tts["chars_synthesized"] == len(answer)


def test_reasoning_chat_without_speak_has_no_tts_key() -> None:
    response = client.post(
        "/reasoning/chat",
        json={
            "messages": [
                {"role": "system", "content": "Keep answers brief."},
                {"role": "user", "content": "Explain mindfulness."},
            ]
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "tts" not in payload


def test_reasoning_chat_with_speak_true_includes_tts() -> None:
    response = client.post(
        "/reasoning/chat?speak=true",
        json={
            "messages": [
                {"role": "system", "content": "Keep answers brief."},
                {"role": "user", "content": "Explain the Eightfold Path."},
            ]
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "answer" in payload
    assert "tts" in payload, "speak=true should add 'tts' key to /reasoning/chat"
    tts = payload["tts"]
    assert "provider" in tts
    assert "chars_synthesized" in tts
    assert "voice" in tts


def test_reasoning_chat_tts_chars_match_answer_length() -> None:
    response = client.post(
        "/reasoning/chat?speak=true",
        json={
            "messages": [
                {"role": "system", "content": "Keep answers brief."},
                {"role": "user", "content": "What is compassion?"},
            ]
        },
    )
    assert response.status_code == 200
    payload = response.json()
    answer = payload.get("answer", "")
    tts = payload.get("tts", {})
    if answer:
        assert tts["chars_synthesized"] == len(answer)
