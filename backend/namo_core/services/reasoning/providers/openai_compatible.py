import httpx
import logging
import traceback

from namo_core.services.reasoning.providers.base import BaseReasoningProvider

logger = logging.getLogger(__name__)


class OpenAICompatibleReasoningProvider(BaseReasoningProvider):
    name = "openai-compatible"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
        system_prompt: str = "You are the Namo Core classroom assistant. Answer clearly and briefly.",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.system_prompt = system_prompt

    async def generate(self, query: str, context: str) -> dict:
        """สร้าง Namo-style prompt: system = คาแรคเตอร์, user = ข้อมูลอ้างอิง + คำถาม"""
        try:
            user_message = self._build_rag_user_message(query=query, context=context)
            content = await self._request_completion(
                [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message},
                ]
            )
            return {
                "query": query,
                "answer": content.strip(),
                "context_excerpt": context[:240],
                "provider": self.name,
                "model": self.model,
            }
        except Exception as exc:
            logger.error(
                "OpenAICompatibleProvider.generate failed: %s\n%s",
                exc,
                traceback.format_exc(),
            )
            raise

    async def chat(self, messages: list[dict], context: str) -> dict:
        """Multi-turn chat: ข้อมูลอ้างอิง inject เข้า system prompt รักษา history"""
        system_content = self.system_prompt
        if context:
            system_content = f"{context}\n\n---\n{self.system_prompt}"

        formatted_messages = [{"role": "system", "content": system_content}]
        formatted_messages.extend(messages)

        try:
            content = await self._request_completion(formatted_messages)
            last_query = next(
                (m["content"] for m in reversed(messages) if m.get("role") == "user"),
                "",
            )
            return {
                "query": last_query,
                "answer": content.strip(),
                "context_excerpt": context[:240] if context else "",
                "provider": self.name,
                "model": self.model,
            }
        except Exception as exc:
            logger.error(
                "OpenAICompatibleProvider.chat failed: %s\n%s",
                exc,
                traceback.format_exc(),
            )
            raise

    @staticmethod
    def _build_rag_user_message(query: str, context: str) -> str:
        """สร้าง user message ในรูปแบบ RAG สำหรับ Namo

        โครงสร้าง:
            ข้อมูลอ้างอิง:
            [context blocks]

            คำถาม: {query}

        การวาง context ไว้ใน user message (ไม่ใช่ system) เหมาะสมกว่าสำหรับ
        RAG เพราะโมเดลให้น้ำหนัก grounding กับ user turn มากกว่า
        """
        if context:
            return f"{context}\n\nคำถาม: {query}"
        return f"คำถาม: {query}"

    async def _request_completion(self, messages: list[dict]) -> str:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                    },
                )
                response.raise_for_status()
                return self._extract_content(response.json())
        except Exception as exc:
            logger.error("OpenAI API call failed: %s\n%s", exc, traceback.format_exc())
            raise

    def _extract_content(self, payload: dict) -> str:
        choices = payload.get("choices") or []
        if not choices:
            raise ValueError("OpenAI-compatible response missing choices.")

        message = choices[0].get("message") or {}
        content = message.get("content")

        if isinstance(content, str) and content.strip():
            return content.strip()

        if isinstance(content, list):
            text_parts: list[str] = []
            for part in content:
                if isinstance(part, str) and part.strip():
                    text_parts.append(part.strip())
                    continue
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        text_parts.append(text.strip())

            if text_parts:
                return "\n".join(text_parts)

        raise ValueError("OpenAI-compatible response missing text content.")
