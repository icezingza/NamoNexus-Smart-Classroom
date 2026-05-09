"""ReasoningService — async Namo Core reasoning with Tripitaka RAG + Session Memory."""

import asyncio
import logging
import time
from asyncio import to_thread
from dataclasses import dataclass, field
from threading import Lock

from namo_core.config.settings import get_settings
from namo_core.services.knowledge.knowledge_service import KnowledgeService
from namo_core.services.knowledge.tripitaka_retriever import get_tripitaka_retriever
from namo_core.services import memory as memory_svc
from namo_core.services.reasoning.providers.factory import build_reasoning_provider
from namo_core.services.reasoning.providers.mock_provider import MockReasoningProvider

_TRIPITAKA_TOP_K = 3
logger = logging.getLogger(__name__)


@dataclass
class _Metrics:
    """Thread-safe counters and latency accumulators for RAG + LLM observability."""

    _lock: Lock = field(default_factory=Lock, repr=False, compare=False)
    tripitaka_calls: int = 0
    tripitaka_total_ms: float = 0.0
    knowledge_calls: int = 0
    knowledge_total_ms: float = 0.0
    llm_calls: int = 0
    llm_total_ms: float = 0.0
    fallback_count: int = 0

    def record_tripitaka(self, elapsed_ms: float) -> None:
        with self._lock:
            self.tripitaka_calls += 1
            self.tripitaka_total_ms += elapsed_ms

    def record_knowledge(self, elapsed_ms: float) -> None:
        with self._lock:
            self.knowledge_calls += 1
            self.knowledge_total_ms += elapsed_ms

    def record_llm(self, elapsed_ms: float) -> None:
        with self._lock:
            self.llm_calls += 1
            self.llm_total_ms += elapsed_ms

    def record_fallback(self) -> None:
        with self._lock:
            self.fallback_count += 1

    def snapshot(self) -> dict:
        with self._lock:

            def _avg(total: float, count: int) -> float | None:
                return round(total / count, 2) if count else None

            return {
                "tripitaka_calls": self.tripitaka_calls,
                "tripitaka_avg_ms": _avg(self.tripitaka_total_ms, self.tripitaka_calls),
                "knowledge_calls": self.knowledge_calls,
                "knowledge_avg_ms": _avg(self.knowledge_total_ms, self.knowledge_calls),
                "llm_calls": self.llm_calls,
                "llm_avg_ms": _avg(self.llm_total_ms, self.llm_calls),
                "fallback_count": self.fallback_count,
            }


_metrics = _Metrics()


def get_metrics() -> dict:
    """Return a snapshot of ReasoningService metrics (thread-safe)."""
    return _metrics.snapshot()


async def _build_tripitaka_context_async(query: str) -> tuple[str, list[dict]]:
    """ดึง Tripitaka RAG chunks และสร้าง 'ข้อมูลอ้างอิง' block สำหรับ LLM prompt (Async)."""
    retriever = get_tripitaka_retriever()
    chunks = await to_thread(retriever.search, query, top_k=_TRIPITAKA_TOP_K)
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
        """Generate a Dhamma explanation using Parallel Tripitaka RAG + EmpathyEngine hint (Async)."""
        from namo_core.api.middleware import request_id_context

        trace_id = request_id_context.get()

        # 1. Parallel Retrieval (O(max(N)) latency)
        async def _timed_tripitaka():
            t0 = time.perf_counter()
            try:
                return await _build_tripitaka_context_async(query)
            finally:
                _metrics.record_tripitaka((time.perf_counter() - t0) * 1000)

        async def _timed_knowledge():
            t0 = time.perf_counter()
            try:
                return await self.knowledge.search_async(query, top_k=3)
            finally:
                _metrics.record_knowledge((time.perf_counter() - t0) * 1000)

        results_nested = await asyncio.gather(
            _timed_tripitaka(), _timed_knowledge(), return_exceptions=True
        )

        # Unpack Tripitaka results
        tripitaka_res = results_nested[0]
        if isinstance(tripitaka_res, Exception):
            logger.error(
                f"[{trace_id}] Tripitaka context build failed: {tripitaka_res}"
            )
            tripitaka_context, tripitaka_chunks = "", []
        else:
            tripitaka_context, tripitaka_chunks = tripitaka_res

        # Unpack Knowledge results (Materials/Lessons)
        results = results_nested[1]
        if isinstance(results, Exception):
            logger.error(f"[{trace_id}] Knowledge search failed: {results}")
            results = []

        legacy_context = self.knowledge.context_builder.build(results)

        # Combine Context
        if tripitaka_context:
            context = tripitaka_context
            if legacy_context:
                context += f"\n\n--- ข้อมูลเสริม ---\n{legacy_context}"
        else:
            context = legacy_context

        context = _prepend_hint(context, teaching_hint)

        # 2. Reasoning Job
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
        """Run a multi-turn chat session with Parallel RAG context + Session Memory (Async)."""
        from namo_core.api.middleware import request_id_context

        trace_id = request_id_context.get()

        if session_id:
            history = await to_thread(memory_svc.get_history, session_id)
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

        # 1. Parallel Retrieval
        async def _timed_tripitaka():
            t0 = time.perf_counter()
            try:
                return await _build_tripitaka_context_async(last_query)
            finally:
                _metrics.record_tripitaka((time.perf_counter() - t0) * 1000)

        async def _timed_knowledge():
            t0 = time.perf_counter()
            try:
                return await self.knowledge.search_async(last_query, top_k=3)
            finally:
                _metrics.record_knowledge((time.perf_counter() - t0) * 1000)

        results_nested = await asyncio.gather(
            _timed_tripitaka(), _timed_knowledge(), return_exceptions=True
        )

        tripitaka_res = results_nested[0]
        if isinstance(tripitaka_res, Exception):
            logger.error(
                f"[{trace_id}] Tripitaka chat context build failed: {tripitaka_res}"
            )
            tripitaka_context, tripitaka_chunks = "", []
        else:
            tripitaka_context, tripitaka_chunks = tripitaka_res

        results = results_nested[1]
        if isinstance(results, Exception):
            logger.error(f"[{trace_id}] Knowledge chat search failed: {results}")
            results = []

        legacy_context = self.knowledge.context_builder.build(results)

        if tripitaka_context:
            context = tripitaka_context
            if legacy_context:
                context += f"\n\n--- ข้อมูลเสริม ---\n{legacy_context}"
        else:
            context = legacy_context

        context = _prepend_hint(context, teaching_hint)

        # 2. Reasoning Job
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
            await to_thread(
                memory_svc.add_turn, session_id, last_query, result.get("answer", "")
            )
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

        t0 = time.perf_counter()
        try:
            if mode == "chat":
                response = await self.provider.chat(
                    messages=messages or [], context=context
                )
            else:
                response = await self.provider.generate(query=query, context=context)
            _metrics.record_llm((time.perf_counter() - t0) * 1000)
        except Exception as exc:
            _metrics.record_llm((time.perf_counter() - t0) * 1000)
            # บันทึกข้อผิดพลาดของ Provider หลักเพื่อการตรวจสอบ (Observability)
            logger.error(
                f"Reasoning provider '{self.provider.name}' failed: {exc}",
                exc_info=True,
            )

            if (
                self.provider.name == "mock"
                or not self.settings.reasoning_allow_mock_fallback
            ):
                raise

            _metrics.record_fallback()
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
