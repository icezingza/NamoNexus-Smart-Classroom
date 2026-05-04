from fastapi import APIRouter, Query
from asyncio import to_thread

from namo_core.services.knowledge.knowledge_service import KnowledgeService
from namo_core.services.knowledge.tripitaka_retriever import (
    get_tripitaka_retriever,
    search_tripitaka,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/search")
async def search_knowledge(
    q: str = Query("", description="Search query", max_length=500),
) -> dict:
    """ค้นหาใน Knowledge Base เดิม (materials + lesson plans) — Phase 1-8"""

    try:
        service = KnowledgeService()
        results = await to_thread(service.search, q)
        if results is None:
            safe_results = []
        elif isinstance(results, dict):
            safe_results = results.get("retrieved_docs", [])
        else:
            safe_results = list(results)

        context_data = await to_thread(service.build_context, q)
    except Exception as exc:
        import logging

        logging.getLogger(__name__).error(f"Knowledge search failed: {exc}")
        safe_results = []
        context_data = ""

    return {
        "query": q,
        "count": len(safe_results),
        "results": safe_results,
        "context": context_data,
    }


@router.get("/tripitaka/search")
async def search_tripitaka_endpoint(
    q: str = Query(
        ..., description="คำถามภาษาไทย/บาลี/อังกฤษ", min_length=1, max_length=500
    ),
    top_k: int = Query(3, description="จำนวน Chunks ที่ต้องการ (1-10)", ge=1, le=10),
) -> dict:
    """
    RAG Search ใน FAISS Tripitaka Index (Phase 11)

    ค้นหา Chunks ที่เกี่ยวข้องกับคำถามด้วย Cosine Similarity
    ใช้สำหรับ Retrieval-Augmented Generation ใน ClassroomPipeline

    Returns:
        query     : คำถามที่รับมา
        count     : จำนวนผลลัพธ์
        results   : list ของ Chunks พร้อม score (0-1)
        retriever_info : สถานะ index (vectors, model, dim)
    """
    results = await to_thread(search_tripitaka, q, top_k)
    retriever = await to_thread(get_tripitaka_retriever)
    return {
        "query": q,
        "top_k": top_k,
        "count": len(results),
        "results": results,
        "retriever_info": retriever.describe(),
    }


@router.get("/tripitaka/status")
async def tripitaka_index_status() -> dict:
    """ตรวจสอบสถานะ FAISS Tripitaka Index — ใช้ใน /health check"""
    retriever = await to_thread(get_tripitaka_retriever)
    return await to_thread(retriever.describe)
