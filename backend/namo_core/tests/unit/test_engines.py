from namo_core.engines.empathy.engine import EmpathyEngine
from namo_core.engines.fusion.engine import FusionEngine
from namo_core.engines.namonexus.engine import NamoNexusEngine
from namo_core.engines.resonance.engine import ResonanceEngine


def test_engine_pipeline_applies_expected_fields() -> None:
    payload = {"query": "mindfulness"}
    payload = NamoNexusEngine().process(payload)
    payload = FusionEngine().process(payload)
    payload = ResonanceEngine().process(payload)
    payload = EmpathyEngine().process(payload)

    assert payload["intent"] == "guide-lesson"
    assert payload["signals_merged"] is True
    assert payload["resonance_score"] > 0
    assert payload["tone"] == "calm"


def test_namonexus_intent_method_present_without_classifier() -> None:
    """Engine without LLM classifier must still return intent_method='keyword'."""
    payload = NamoNexusEngine().process({"query": "quiz me on karma"})
    assert payload["intent"] == "quiz-lesson"
    assert payload["intent_method"] == "keyword"


def test_namonexus_keyword_fallback_maps_all_intents() -> None:
    cases = {
        "quiz me": "quiz-lesson",
        "reflect on suffering": "reflection",
        "give me a summary": "summary-lesson",
        "explain the middle way": "guide-lesson",  # default
    }
    for query, expected_intent in cases.items():
        result = NamoNexusEngine().process({"query": query})
        assert result["intent"] == expected_intent, f"Failed for: {query!r}"


def test_empathy_engine_provides_student_state() -> None:
    payload = {"resonance_score": 0.8}
    result = EmpathyEngine().process(payload)
    assert "student_state" in result
    assert isinstance(result["student_state"], str)
