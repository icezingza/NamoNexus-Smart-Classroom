from namo_core.modules.reasoning.llm_reasoner import LLMReasoner
from namo_core.services.reasoning.providers.base import BaseReasoningProvider


class MockReasoningProvider(BaseReasoningProvider):
    name = "mock"

    def __init__(self) -> None:
        self.reasoner = LLMReasoner()

    def generate(self, query: str, context: str) -> dict:
        response = self.reasoner.respond(query=query, context=context)
        response["provider"] = self.name
        return response

    def chat(self, messages: list[dict], context: str) -> dict:
        last_query = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        response = self.reasoner.respond(query=last_query, context=context)
        response["provider"] = self.name
        return response
