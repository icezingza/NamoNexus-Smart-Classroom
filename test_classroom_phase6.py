# -*- coding: utf-8 -*-
"""
test_classroom_phase6.py - Integration Tests for Phase 5/6 Core Services
=======================================================================

Tests the interaction between core components:
- KnowledgeService (RAG)
- ReasoningService (LLM)
- EmotionEngine (Stateful Emotion Tracking)
- ClassroomState (Shared Context)

This test file ensures that the foundational services that power the Phase 7
`ClassroomPipeline` work correctly together. It uses `pytest` and `mocker`
to isolate components and simulate external dependencies.

"""

import pytest
from unittest.mock import MagicMock

# Assume these are the core components from your modules
from namo_core.services.knowledge.knowledge_service import KnowledgeService
from namo_core.services.reasoning.reasoner import ReasoningService
from namo_core.engines.emotion_engine import EmotionEngine
from namo_core.modules.tts.synthesizer import SpeechSynthesizer
from namo_core.models.classroom_state import ClassroomState, Student
from namo_core.config.settings import get_settings


@pytest.fixture(scope="module")
def settings():
    """Load application settings once per module."""
    return get_settings()


@pytest.fixture
def mock_knowledge_service(mocker):
    """Fixture to create a mocked KnowledgeService."""
    # Mock the FAISS index loading and searching
    mocker.patch("faiss.read_index", return_value=MagicMock())
    mocker.patch(
        "namo_core.services.knowledge.knowledge_service.KnowledgeService._load_metadata",
        return_value={},
    )
    service = KnowledgeService()
    # Mock the search method to return predictable results
    service.search = MagicMock(
        return_value={
            "query": "test query",
            "retrieved_docs": [
                {"source": "TPD/01.txt", "content": "This is a test document."}
            ],
            "search_time_ms": 10.0,
        }
    )
    return service


@pytest.fixture
def mock_reasoning_service(mocker):
    """Fixture to create a mocked ReasoningService."""
    service = ReasoningService(provider="mock")
    # Mock the actual call to the LLM
    service.get_response = MagicMock(
        return_value={
            "answer": "This is a mock LLM answer.",
            "sources": ["TPD/01.txt"],
            "provider": "mock",
            "model": "mock-model",
            "latency_ms": 150.0,
        }
    )
    return service


@pytest.fixture
def mock_tts_service(mocker):
    """Fixture for a mocked SpeechSynthesizer."""
    # เราสามารถสร้าง instance จาก 'mock' provider ซึ่งปลอดภัยสำหรับการทดสอบ
    # จากนั้นเราจะ mock method ที่ใช้สังเคราะห์เสียงเพื่อควบคุมผลลัพธ์
    service = SpeechSynthesizer(provider="mock")

    # Mock method ที่คืนค่าเสียงเป็น base64
    mocker.patch.object(
        service,
        "synthesize_to_base64",
        return_value={
            "audio_base64": "aGVsbG8gd29ybGQ=",  # "hello world" encoded
            "provider": "mock",
            "voice": "test-voice",
        },
    )
    return service


@pytest.fixture
def classroom_state():
    """Fixture for a clean ClassroomState instance for each test."""
    state = ClassroomState()
    state.start_session(session_id="test_session", teacher_id="teacher_01")
    state.add_student(Student(id="student_01", name="Alice"))
    return state


def test_phase6_simple_integration(
    mock_knowledge_service, mock_reasoning_service, classroom_state
):
    """
    Test a simple RAG pipeline: Query -> Knowledge Search -> Reasoning.
    This verifies the basic data flow between the two main services.
    """
    query = "What is the meaning of life?"

    # 1. Knowledge Retrieval
    knowledge_result = mock_knowledge_service.search(query)
    assert "retrieved_docs" in knowledge_result
    assert len(knowledge_result["retrieved_docs"]) > 0
    mock_knowledge_service.search.assert_called_once_with(query)

    # 2. Reasoning
    reasoning_result = mock_reasoning_service.get_response(
        query=query, context_docs=knowledge_result["retrieved_docs"]
    )
    assert "answer" in reasoning_result
    assert reasoning_result["answer"] == "This is a mock LLM answer."
    mock_reasoning_service.get_response.assert_called_once()


def test_emotion_engine_state_update(classroom_state):
    """
    Test that the EmotionEngine correctly processes signals and updates
    the student's emotional state within the shared ClassroomState.
    """
    # Get the emotion engine for a specific student
    emotion_engine = classroom_state.get_student("student_01").emotion_engine
    assert emotion_engine.get_current_state()["state"] == "attentive"  # Default state

    # Simulate receiving a low attention signal from the vision module
    perception_signals = {"attention_score": 0.2, "engagement": "passive"}
    emotion_engine.process_signals(perception_signals)

    # After multiple low signals, the state should change
    for _ in range(5):
        emotion_engine.process_signals(perception_signals)

    updated_state = emotion_engine.get_current_state()
    assert updated_state["state"] == "wandering"
    assert updated_state["smoothed_attention"] < 0.5


def test_full_loop_with_emotion_context(
    mock_knowledge_service, mock_reasoning_service, classroom_state
):
    """
    Test the full loop where student's emotional state is passed to the
    reasoning service as a "teaching_hint".
    """
    query = "I don't understand."
    student = classroom_state.get_student("student_01")

    # Make student's state "confused"
    student.emotion_engine.process_signals({"sentiment": "negative", "energy": 0.3})
    for _ in range(3):
        student.emotion_engine.process_signals({"sentiment": "negative"})

    teaching_hint = student.emotion_engine.get_teaching_hint()
    assert "confused" in teaching_hint

    # Check if the hint is passed to the reasoning service
    mock_reasoning_service.get_response(
        query=query, context_docs=[], teaching_hint=teaching_hint
    )
    mock_reasoning_service.get_response.assert_called_with(
        query=query, context_docs=[], teaching_hint=teaching_hint
    )
    print("Successfully tested that teaching_hint is passed to the reasoner.")


def test_tts_synthesis_service(mock_tts_service):
    """
    Test the SpeechSynthesizer service can be called and returns a base64 string.
    This verifies that the TTS module is wired up correctly for pipeline use.
    """
    text_to_speak = "สวัสดีครับ, นี่คือการทดสอบเสียง"
    voice_id = "th-TH-PremwadeeNeural"

    # 1. เรียกใช้ method สังเคราะห์เสียง
    result = mock_tts_service.synthesize_to_base64(text_to_speak, voice=voice_id)

    # 2. ตรวจสอบว่า mock ถูกเรียกด้วย argument ที่ถูกต้อง
    mock_tts_service.synthesize_to_base64.assert_called_once_with(
        text_to_speak, voice=voice_id
    )

    # 3. ตรวจสอบว่าได้รับผลลัพธ์เป็น dictionary ที่มีข้อมูลเสียงตามที่ mock ไว้
    assert "audio_base64" in result
    assert result["audio_base64"] == "aGVsbG8gd29ybGQ="
    print("\nSuccessfully tested that SpeechSynthesizer can be called.")


def test_rag_empty_result_fallback(
    mock_knowledge_service, mock_reasoning_service, classroom_state
):
    """
    Test the pipeline behavior when the KnowledgeService (RAG) finds no relevant documents.
    The ReasoningService should still be called, but with an empty context.
    """
    query = "คำถามที่ไม่มีในฐานข้อมูล"

    # 1. Modify the mock to return an empty list of documents for this specific test
    mock_knowledge_service.search.return_value = {
        "query": query,
        "retrieved_docs": [],
        "search_time_ms": 5.0,
    }

    # 2. Execute Knowledge Search
    knowledge_result = mock_knowledge_service.search(query)
    assert len(knowledge_result["retrieved_docs"]) == 0

    # 3. Execute Reasoning with empty context
    mock_reasoning_service.get_response(
        query=query, context_docs=knowledge_result["retrieved_docs"]
    )

    # 4. Verify ReasoningService was called with an empty list for context_docs
    mock_reasoning_service.get_response.assert_called_with(query=query, context_docs=[])
    print("\nSuccessfully tested RAG empty result scenario.")
