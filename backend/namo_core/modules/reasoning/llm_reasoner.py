class LLMReasoner:
    def respond(self, query: str, context: str) -> dict:
        sentences = [segment.strip() for segment in context.splitlines() if segment.strip()]
        context_hint = sentences[0] if sentences else "No direct supporting material was found."
        return {
            "query": query,
            "answer": f"Recovered teaching response: {query}. Key point: {context_hint}",
            "context_excerpt": context[:240],
        }
