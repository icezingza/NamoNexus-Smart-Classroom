from abc import ABC, abstractmethod


class BaseReasoningProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(self, query: str, context: str) -> dict:
        """Generate a structured response for the given query (async)."""

    @abstractmethod
    async def chat(self, messages: list[dict], context: str) -> dict:
        """Generate a response using chat history (async)."""
