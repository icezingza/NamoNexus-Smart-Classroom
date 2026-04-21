from namo_core.config.settings import get_settings
from namo_core.services.knowledge.knowledge_service import KnowledgeService
from namo_core.services.knowledge.tripitaka_retriever import search_tripitaka
from namo_core.services.memory import manager as memory
from namo_core.services.reasoning.providers.factory import build_reasoning_provider
from namo_core.services.reasoning.providers.mock_provider import MockReasoningProvider

# จำนวน Tripitaka chunks ที่ดึงมาต่อ 1 query
_TRIPITAKA_TOP_K = 3


def _build_tripitaka_context(query: str) -> tuple[str, list[dict]]:
    """ดึง Tripitaka RAG chunks และสร้าง 'ข้อมูลอ้างอิง' block สำหรับ LLM prompt

    Args:
        query: คำถามของผู้ใช้

    Returns:
        Tuple ของ (context_string, raw_chunks)
        context_string: พร้อม inject เข้า prompt ได้ทันที
        raw_chunks: list ดิบสำหรับ _build_response() sources
    """
    chunks = search_tripitaka(query, top_k=_TRIPITAKA_TOP_K)
    if not chunks:
        return "", []

    lines = ["ข้อมูลอ้างอิง (พระไตรปิฎก):"]
    for i, c in enumerate(chunks, 1):
        lines.append(f"\n[{i}] {c['title']} (score={c['score']:.2f})")
        lines.append(c["text"])
        if i < len(chunks):
            lines.append("---")

    return "\n".join(lines), chunks


def _prepend_hint(context: str, teaching_hint: str) -> str:
    """Prepend a teaching hint to the knowledge context when provided.

    The hint is formatted as a bracketed instruction so the LLM treats it
    as guidance rather than knowledge content.

    Args:
        context: Knowledge context string.
        teaching_hint: Thai-language adaptation instruction from EmpathyEngine.

    Returns:
        Context string with hint prepended, or unchanged if hint is empty.
    """
    if not teaching_hint:
        return context
    return f"[คำแนะนำการสอน: {teaching_hint}]\n\n{context}"


class ReasoningService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.provider, self.provider_metadata = build_reasoning_provider(self.settings)
        self.knowledge = KnowledgeService()

    def explain(self, query: str, teaching_hint: str = "") -> dict:
        """Generate a Dhamma explanation using Tripitaka RAG + EmpathyEngine hint.

        Context priority:
          1. Tripitaka FAISS chunks (Phase 11 RAG) — injected as 'ข้อมูลอ้างอิง'
          2. KnowledgeService results (materials/lessons fallback)
          3. teaching_hint from EmpathyEngine prepended as bracketed instruction

        Args:
            query: Student's question or topic.
            teaching_hint: Thai-language instruction from EmpathyEngine describing
                           how the LLM should adapt its explanation style.
        """
        # Phase 11 RAG: Tripitaka FAISS — primary context source
        tripitaka_context, tripitaka_chunks = _build_tripitaka_context(query)

        # Legacy context: materials + lesson plans — used as supplement/fallback
        results = self.knowledge.search(query)
        legacy_context = self.knowledge.context_builder.build(results or self.knowledge.search(""))

        # Merge: Tripitaka RAG first, legacy below as supplement
        if tripitaka_context:
            context = tripitaka_context
            if legacy_context:
                context += f"\n\n--- ข้อมูลเสริม ---\n{legacy_context}"
        else:
            context = legacy_context

        context = _prepend_hint(context, teaching_hint)

        response, metadata = self._run_provider(
            mode="generate",
            query=query,
            context=context,
        )
        return self._build_response(
            response=response,
            metadata=metadata,
            results=results,
            tripitaka_chunks=tripitaka_chunks,
            context=context,
        )

    def chat(self, messages: list[dict], teaching_hint: str = "", session_id: str = "") -> dict:
        """Run a multi-turn chat session with Tripitaka RAG context + Session Memory.

        Args:
            messages: Conversation history as list of role/content dicts.
            teaching_hint: Thai-language instruction from EmpathyEngine.
            session_id: ถ้าระบุ จะ prepend history จาก SessionMemory ก่อน messages
        """
        # ── Session Memory (Hippocampus) ──────────────────────────────
        if session_id:
            history = memory.get_history(session_id)
            if history:
                messages = history + list(messages)

        last_query = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")

        # Phase 11 RAG: Tripitaka FAISS
        tripitaka_context, tripitaka_chunks = _build_tripitaka_context(last_query)

        # Legacy context
        results = self.knowledge.search(last_query)
        legacy_context = self.knowledge.context_builder.build(results or self.knowledge.search(""))

        if tripitaka_context:
            context = tripitaka_context
            if legacy_context:
                context += f"\n\n--- ข้อมูลเสริม ---\n{legacy_context}"
        else:
            context = legacy_context

        context = _prepend_hint(context, teaching_hint)

        response, metadata = self._run_provider(
            mode="chat",
            query=last_query,
            messages=messages,
            context=context,
        )
        result = self._build_response(
            response=response,
            metadata=metadata,
            results=results,
            tripitaka_chunks=tripitaka_chunks,
            context=context,
        )
        # ── บันทึก turn ลง Session Memory ──────────────────────────────
        if session_id and last_query:
            memory.add_turn(session_id, last_query, result.get("answer", ""))
        return result

    def _run_provider(
        self,
        mode: str,
        query: str,
        context: str,
        messages: list[dict] | None = None,
    ) -> tuple[dict, dict]:
        metadata = dict(self.provider_metadata)

        try:
            if mode == "chat":
                response = self.provider.chat(messages=messages or [], context=context)
            else:
                response = self.provider.generate(query=query, context=context)
        except Exception as exc:
            if self.provider.name == "mock" or not self.settings.reasoning_allow_mock_fallback:
                raise

            fallback_provider = MockReasoningProvider()
            if mode == "chat":
                response = fallback_provider.chat(messages=messages or [], context=context)
            else:
                response = fallback_provider.generate(query=query, context=context)

            metadata["attempted_provider"] = self.provider.name
            metadata["name"] = fallback_provider.name
            metadata["active_provider"] = fallback_provider.name
            metadata["fallback_reason"] = "Reasoning provider request failed; using mock provider."
            metadata["provider_error"] = exc.__class__.__name__
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

        # Tripitaka RAG sources (Phase 11) — แสดงก่อน legacy sources
        tripitaka_sources = [
            {
                "id": c["chunk_id"],
                "title": c["title"],
                "source": "tripitaka_faiss",
                "score": c.get("score"),
                "source_url": c.get("source_url", ""),
            }
            for c in (tripitaka_chunks or [])
        ]

        # Legacy knowledge sources
        legacy_sources = [
            {
                "id": item["id"],
                "title": item["title"],
                "source": item["source"],
                "score": item.get("score"),
            }
            for item in results[:5]
        ]

        response["sources"] = tripitaka_sources + legacy_sources
        response["provider_metadata"] = metadata
        return response
