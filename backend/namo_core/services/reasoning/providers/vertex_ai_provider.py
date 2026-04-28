"""Vertex AI (Gemini 1.5 Pro) Reasoning Provider."""
from __future__ import annotations

import logging
from asyncio import to_thread

from namo_core.services.reasoning.providers.base import BaseReasoningProvider

logger = logging.getLogger(__name__)


class VertexAIReasoningProvider(BaseReasoningProvider):
    name = "vertex-ai"

    def __init__(
        self,
        model: str = "gemini-1.5-pro",
        system_prompt: str = "",
        timeout_seconds: float = 30.0,
        location: str = "asia-southeast1",
    ) -> None:
        self.model = model
        
        # Enforce Clean Room Prompting & Data Residency Isolation
        clean_room_rule = (
            "\n\n[SECURITY FIRST - CLEAN ROOM PROMPTING]\n"
            "You are operating in an Anonymization Layer. You will *never* receive "
            "identifiable student details (PII). All inquiries are anonymized. "
            "Address the user generically as 'นักเรียน' (Student) or 'ลูก' (Child). "
            "Provide answers strictly grounded in the Wisdom Context (พระไตรปิฎก) provided."
        )
        self.system_prompt = system_prompt + clean_room_rule

        self.timeout_seconds = timeout_seconds

        try:
            from google import genai
            self.genai = genai
            self.client = genai.Client(vertexai=True, location=location)
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "google-genai package is not installed."
            ) from exc
        except Exception as exc:
            logger.warning("GCP Credentials missing for Vertex AI.")
            raise RuntimeError(f"Vertex AI init failed: {exc}") from exc

    async def generate(self, query: str, context: str) -> dict:
        prompt = f"บริบทธรรมะ (The Wisdom Context):\n{context}\n\nคำถามนักเรียน (The Raw Inquiry):\n{query}"

        try:
            response = await to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=self.genai.types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    temperature=0.3,
                ),
            )
            return {
                "query": query,
                "answer": response.text,
                "provider": self.name,
            }
        except Exception as exc:
            logger.error("Vertex AI generate failed: %s", exc)
            raise

    async def chat(self, messages: list[dict], context: str) -> dict:
        last_query = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        contents = []

        for i, m in enumerate(messages):
            role = "user" if m.get("role") == "user" else "model"
            content_text = m.get("content", "")

            # Inject context strictly into the latest user inquiry block
            if i == len(messages) - 1 and role == "user":
                content_text = f"บริบทธรรมะ (The Wisdom Context):\n{context}\n\nคำถามนักเรียน (The Raw Inquiry):\n{content_text}"

            contents.append(
                self.genai.types.Content(
                    role=role,
                    parts=[self.genai.types.Part.from_text(text=content_text)]
                )
            )

        try:
            response = await to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=contents,
                config=self.genai.types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    temperature=0.3,
                ),
            )
            return {
                "query": last_query,
                "answer": response.text,
                "provider": self.name,
            }
        except Exception as exc:
            logger.error("Vertex AI chat failed: %s", exc)
            raise
