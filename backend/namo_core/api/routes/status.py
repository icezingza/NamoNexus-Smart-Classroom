from fastapi import APIRouter

from namo_core.services.classroom.classroom_service import ClassroomService
from namo_core.services.knowledge.knowledge_service import KnowledgeService
from namo_core.services.orchestrator import orchestrator
from namo_core.config.settings import get_settings

# ตรวจสอบและสร้างการเชื่อมต่อ Database (Phase 12)
try:
    from namo_core.db.database import engine, Base
    import namo_core.models.feedback  # สำคัญ: ต้อง import model เพื่อให้ SQLAlchemy รู้จักตาราง

    # สร้างตารางอัตโนมัติหากยังไม่มีในระบบ
    Base.metadata.create_all(bind=engine)
    db_status = "connected"
except Exception as e:
    db_status = f"error: {str(e)}"

router = APIRouter(tags=["status"])


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
