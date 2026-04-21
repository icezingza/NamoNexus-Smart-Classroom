"""IntentClassifier — uses the configured LLM provider to classify query intent.

Falls back to keyword matching automatically when:
- The active provider is 'mock' (no real LLM configured)
- The LLM call fails for any reason (network, timeout, parse error)

This keeps the engine pipeline safe and fast in all environments.
"""
from __future__ import annotations

import re

from namo_core.config.settings import get_settings
from namo_core.services.reasoning.providers.base import BaseReasoningProvider
from namo_core.services.reasoning.providers.factory import build_reasoning_provider

# ---------------------------------------------------------------------------
# Known intent labels (single source of truth shared with the engine)
# ---------------------------------------------------------------------------
KNOWN_INTENTS: list[str] = [
    "guide-lesson",
    "quiz-lesson",
    "reflection",
    "summary-lesson",
]
DEFAULT_INTENT = "guide-lesson"

# Keyword fallback table — used when LLM is unavailable
_KEYWORD_MAP: dict[str, list[str]] = {
    "quiz-lesson": ["quiz", "test", "exam", "question"],
    "reflection": ["reflect", "contemplate", "meditate", "ponder"],
    "summary-lesson": ["summarize", "summary", "overview", "recap"],
}

# Prompt for the LLM — short, structured, deterministic
_INTENT_SYSTEM_PROMPT = (
    "You are an intent classifier for a Buddhist classroom assistant. "
    "Respond with ONLY one of these labels, nothing else: "
    + ", ".join(KNOWN_INTENTS)
    + "."
)
_INTENT_USER_TEMPLATE = (
    "Classify the intent of this student query.\n"
    "Query: {query}\n"
    "Intent label:"
)


def _keyword_classify(query: str) -> str:
    """Pure keyword fallback — always succeeds."""
    lower = query.lower()
    for intent, keywords in _KEYWORD_MAP.items():
        if any(kw in lower for kw in keywords):
            return intent
    return DEFAULT_INTENT


def _parse_intent(raw: str) -> str:
    """Extract the first matching intent label from the LLM raw text."""
    for label in KNOWN_INTENTS:
        if label in raw.lower():
            return label
    # Try JSON {"intent": "..."} shape just in case
    match = re.search(r'"intent"\s*:\s*"([^"]+)"', raw, re.IGNORECASE)
    if match and match.group(1) in KNOWN_INTENTS:
        return match.group(1)
    return DEFAULT_INTENT


class IntentClassifier:
    """Classifies query intent via LLM with automatic keyword fallback."""

    def __init__(self, provider: BaseReasoningProvider | None = None) -> None:
        if provider is None:
            settings = get_settings()
            provider, _ = build_reasoning_provider(settings)
        self._provider = provider

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return self._provider.name

    def classify(self, query: str) -> tuple[str, str]:
        """Return ``(intent, method)`` where method is ``'llm'`` or ``'keyword'``."""
        # Skip LLM call when mock — it won't add any insight over keywords
        if self._provider.name == "mock":
            return _keyword_classify(query), "keyword"

        try:
            response = self._provider.generate(
                query=_INTENT_USER_TEMPLATE.format(query=query),
                context="",  # intent detection needs no knowledge context
            )
            raw_text: str = response.get("answer", "") or str(response)
            intent = _parse_intent(raw_text)
            return intent, "llm"
        except Exception:
            # Any LLM failure → silent fallback to keywords
            return _keyword_classify(query), "keyword"
