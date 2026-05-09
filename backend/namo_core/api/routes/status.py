import logging
from fastapi import APIRouter

from namo_core.services.classroom.classroom_service import ClassroomService
from namo_core.services.knowledge.knowledge_service import KnowledgeService
from namo_core.services.orchestrator import orchestrator
from namo_core.config.settings import get_settings
from namo_core.services.reasoning.reasoner import get_metrics as get_reasoning_metrics

logger = logging.getLogger(__name__)

# ตรวจสอบและสร้างการเชื่อมต่อ Database (Phase 12)
try:
    from namo_core.database.core import engine

    db_status = "connected"
except Exception as e:
    db_status = f"error: {str(e)}"

router = APIRouter(tags=["status"])


async def _redis_ping() -> str:
    """Return 'connected' on successful PING, or an error string."""
    settings = get_settings()
    if not settings.redis_url:
        return "not_configured"
    r = None
    try:
        from namo_core.utils.redis_factory import make_redis

        r = make_redis()
        await r.execute_command("PING")
        return "connected"
    except Exception as exc:
        logger.error(f"Redis status check failed: {exc}")
        return f"error: {exc}"
    finally:
        if r is not None:
            await r.aclose()


@router.get("/metrics")
async def metrics() -> dict:
    """RAG + LLM performance counters (since last process start)."""
    return get_reasoning_metrics()


@router.get("/status")
async def status() -> dict:
    classroom = ClassroomService()
    knowledge = KnowledgeService()
    settings = get_settings()

    # ตรวจสอบสถานะการ Initialized ของ Singleton เพื่อป้องกันการโหลดโมเดลซ้ำ (Timeout)
    orchestrator_ready = getattr(orchestrator, "_initialized", False)

    return {
        "project": "Namo Core",
        "backend": "online",
        "database": db_status,
        "redis": await _redis_ping(),
        "knowledge_items": getattr(knowledge, "catalog_size", 0),
        "knowledge_index": getattr(knowledge, "index_summary", lambda: {})(),
        "classroom": await classroom.get_session_summary(),
        "orchestrator_ready": orchestrator_ready,
        "feature_flags": {
            "emotion_engine": True,
            "knowledge": True,
            "tts": getattr(settings, "enable_tts", True),
        },
    }
