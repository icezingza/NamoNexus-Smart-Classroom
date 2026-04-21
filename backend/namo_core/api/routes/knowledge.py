from fastapi import APIRouter, Query

from namo_core.services.knowledge.knowledge_service import KnowledgeService
from namo_core.services.knowledge.tripitaka_retriever import (
    get_tripitaka_retriever,
    search_tripitaka,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/search")
def search_knowledge(q: str = Query("", description="Search query", max_length=500)) -> dict:
    """ค้นหาใน Knowledge Base เดิม (materials + lesson plans) — Phase 1-8"""
    service = KnowledgeService()
    results = service.search(q)
    return {
        "query": q,
        "count": len(results),
        "results": results,
        "context": service.build_context(q),
    }


@router.get("/tripitaka/search")
def search_tripitaka_endpoint(
    q: str = Query(..., description="คำถามภาษาไทย/บาลี/อังกฤษ", min_length=1, max_length=500),
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
    results = search_tripitaka(q, top_k=top_k)
    retriever = get_tripitaka_retriever()
    return {
        "query":          q,
        "top_k":          top_k,
        "count":          len(results),
        "results":        results,
        "retriever_info": retriever.describe(),
    }


@router.get("/tripitaka/status")
def tripitaka_index_status() -> dict:
    """ตรวจสอบสถานะ FAISS Tripitaka Index — ใช้ใน /health check"""
    retriever = get_tripitaka_retriever()
    return retriever.describe()

