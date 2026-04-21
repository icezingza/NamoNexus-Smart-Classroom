from __future__ import annotations

from namo_core.core.base_engine import BaseEngine

# KNOWN_INTENTS and keyword table re-imported for standalone fallback
# (when engine is used without an injected classifier)
_KEYWORD_MAP: dict[str, list[str]] = {
    "quiz-lesson": ["quiz", "test", "exam", "question"],
    "reflection": ["reflect", "contemplate", "meditate", "ponder"],
    "summary-lesson": ["summarize", "summary", "overview", "recap"],
}
_DEFAULT_INTENT = "guide-lesson"


def _keyword_classify(query: str) -> str:
    lower = query.lower()
    for intent, keywords in _KEYWORD_MAP.items():
        if any(kw in lower for kw in keywords):
            return intent
    return _DEFAULT_INTENT


class NamoNexusEngine(BaseEngine):
    name = "namonexus"

    def __init__(self, intent_classifier=None) -> None:  # type: ignore[override]
        # intent_classifier: IntentClassifier | None
        # Typed loosely to avoid a circular/heavy import at module load time.
        self._classifier = intent_classifier

    def process(self, payload: dict) -> dict:
        query = str(payload.get("query", ""))

        if self._classifier is not None:
            intent, method = self._classifier.classify(query)
        else:
            intent = _keyword_classify(query)
            method = "keyword"

        updated = dict(payload)
        updated["intent"] = intent
        updated["intent_method"] = method
        return updated
