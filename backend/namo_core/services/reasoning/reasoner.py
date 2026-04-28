"""ReasoningService — async Namo Core reasoning with Tripitaka RAG + Session Memory."""

from __future__ import annotations

from asyncio import to_thread

from namo_core.config.settings import get_settings
from namo_core.services.knowledge.knowledge_service import KnowledgeService
from namo_core.services.knowledge.tripitaka_retriever import search_tripitaka
from namo_core.services import memory as memory_svc
from namo_core.services.reasoning.providers.factory import build_reasoning_provider
from namo_core.services.reasoning.providers.mock_provider import MockReasoningProvider

_TRIPITAKA_TOP_K = 3


def _build_tripitaka_context(query: str) -> tuple[str, list[dict]]:
    """ดึง Tripitaka RAG chunks และสร้าง 'ข้อมูลอ้างอิง' block สำหรับ LLM prompt."""
    chunks = search_tripitaka(query, top_k=_TRIPITAKA_TOP_K)
    if not chunks:
        return "", []

    lines = ["ข้อมูลอ้างอิง (พระไตรปิฎก):"]
    for i, c in enumerate(chunks, 1):
        title = c.get("title", "ไม่ระบุ") if isinstance(c, dict) else "ไม่ระบุ"
        score = c.get("score", 0.0) if isinstance(c, dict) else 0.0
        text = c.get("text", "") if isinstance(c, dict) else ""
        lines.append(f"\n[{i}] {title} (score={score:.2f})")
        lines.append(text)
        if i < len(chunks):
            lines.append("---")

    return "\n".join(lines), chunks


def _prepend_hint(context: str, teaching_hint: str) -> str:
    """Prepend a teaching hint to the knowledge context when provided."""
    if not teaching_hint:
        return context
    return f"[คำแนะนำการสอน: {teaching_hint}]\n\n{context}"


class ReasoningService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.provider, self.provider_metadata = build_reasoning_provider(self.settings)
        self.knowledge = KnowledgeService()

    async def explain(self, query: str, teaching_hint: str = "") -> dict:
        """Generate a Dhamma explanation using Tripitaka RAG + EmpathyEngine hint (async).

        Context priority:
          1. Tripitaka FAISS chunks (Phase 11 RAG) — injected as 'ข้อมูลอ้างอิง'
          2. KnowledgeService results (materials/lessons fallback)
          3. teaching_hint from EmpathyEngine prepended as bracketed instruction
        """
        # CPU-bound FAISS + file I/O → run in thread pool
        tripitaka_context, tripitaka_chunks = await to_thread(
            _build_tripitaka_context, query
        )
        results = await to_thread(self.knowledge.search, query)
        legacy_context = self.knowledge.context_builder.build(
            results or await to_thread(self.knowledge.search, "")
        )

        if tripitaka_context:
            context = tripitaka_context
            if legacy_context:
                context += f"\n\n--- ข้อมูลเสริม ---\n{legacy_context}"
        else:
            context = legacy_context

        context = _prepend_hint(context, teaching_hint)

        response, metadata = await self._run_provider(
            mode="generate", query=query, context=context
        )
        return self._build_response(
            response=response,
            metadata=metadata,
            results=results,
            tripitaka_chunks=tripitaka_chunks,
            context=context,
        )

    async def chat(
        self,
        messages: list[dict],
        teaching_hint: str = "",
        session_id: str = "",
    ) -> dict:
        """Run a multi-turn chat session with Tripitaka RAG context + Session Memory (async)."""
        if session_id:
            history = memory_svc.get_history(session_id)
            if history:
                messages = history + list(messages)

        last_query = next(
            (
                m.get("content", "")
                for m in reversed(messages)
                if isinstance(m, dict) and m.get("role") == "user"
            ),
            "",
        )

        tripitaka_context, tripitaka_chunks = await to_thread(
            _build_tripitaka_context, last_query
        )
        results = await to_thread(self.knowledge.search, last_query)
        legacy_context = self.knowledge.context_builder.build(
            results or await to_thread(self.knowledge.search, "")
        )

        if tripitaka_context:
            context = tripitaka_context
            if legacy_context:
                context += f"\n\n--- ข้อมูลเสริม ---\n{legacy_context}"
        else:
            context = legacy_context

        context = _prepend_hint(context, teaching_hint)

        response, metadata = await self._run_provider(
            mode="chat", query=last_query, messages=messages, context=context
        )
        result = self._build_response(
            response=response,
            metadata=metadata,
            results=results,
            tripitaka_chunks=tripitaka_chunks,
            context=context,
        )

        if session_id and last_query:
            memory_svc.add_turn(session_id, last_query, result.get("answer", ""))
        return result

    async def _run_provider(
        self,
        mode: str,
        query: str,
        context: str,
        messages: list[dict] | None = None,
    ) -> tuple[dict, dict]:
        """Dispatch to LLM provider (async). Falls back to mock on failure."""
        metadata = dict(self.provider_metadata)

        try:
            if mode == "chat":
                response = await self.provider.chat(
                    messages=messages or [], context=context
                )
            else:
                response = await self.provider.generate(query=query, context=context)
        except Exception as exc:
            if (
                self.provider.name == "mock"
                or not self.settings.reasoning_allow_mock_fallback
            ):
                raise

            fallback = MockReasoningProvider()
            if mode == "chat":
                response = await fallback.chat(messages=messages or [], context=context)
            else:
                response = await fallback.generate(query=query, context=context)

            metadata.update(
                {
                    "attempted_provider": self.provider.name,
                    "name": fallback.name,
                    "active_provider": fallback.name,
                    "fallback_reason": "Reasoning provider request failed; using mock provider.",
                    "provider_error": exc.__class__.__name__,
                }
            )
            return response, metadata

        metadata["name"] = response.get("provider", self.provider.name)
        metadata["active_provider"] = response.get("provider", self.provider.name)
        return response, metadata

    def _build_response(
        self,
        response: dict,
        metadata: dict,
        results: list[dict],
        context: str,
        tripitaka_chunks: list[dict] | None = None,
    ) -> dict:
        response["context"] = context

        def _safe_score(v) -> float | None:
            """Convert numpy.float32/float64 → Python float for JSON serialization."""
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        tripitaka_sources = []
        for c in tripitaka_chunks or []:
            if isinstance(c, dict):
                tripitaka_sources.append(
                    {
                        "id": c.get("chunk_id", ""),
                        "title": c.get("title", ""),
                        "source": "tripitaka_faiss",
                        "score": _safe_score(c.get("score")),
                        "source_url": c.get("source_url", ""),
                    }
                )

        legacy_sources = []
        # เผื่อกรณีที่ KnowledgeService.search() คืนค่ามาเป็น dict แทนที่จะเป็น list
        safe_results = (
            results.get("retrieved_docs", [])
            if isinstance(results, dict)
            else (results or [])
        )
        for item in safe_results[:5]:
            if isinstance(item, dict):
                try:
                    legacy_sources.append(
                        {
                            "id": item.get("id", item.get("chunk_id", "")),
                            "title": item.get("title", ""),
                            "source": item.get(
                                "source", item.get("source_cat", "knowledge")
                            ),
                            "score": _safe_score(item.get("score")),
                        }
                    )
                except Exception:
                    pass  # ข้าม source ตัวที่มีปัญหา ไม่ต้องให้กระทบกับคำตอบหลัก

        response["sources"] = tripitaka_sources + legacy_sources
        response["provider_metadata"] = metadata
        return response
