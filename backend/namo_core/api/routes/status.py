from fastapi import APIRouter

from namo_core.services.classroom.classroom_service import ClassroomService
from namo_core.services.knowledge.knowledge_service import KnowledgeService
from namo_core.services.orchestrator import orchestrator

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
def status() -> dict:
    classroom = ClassroomService()
    knowledge = KnowledgeService()

    # ตรวจสอบสถานะการ Initialized ของ Singleton เพื่อป้องกันการโหลดโมเดลซ้ำ (Timeout)
    orchestrator_ready = getattr(orchestrator, "_initialized", False)

    return {
        "project": "Namo Core",
        "backend": "online",
        "database": db_status,
        "knowledge_items": knowledge.catalog_size,
        "knowledge_index": knowledge.index_summary(),
        "classroom": classroom.get_session_summary(),
        "orchestrator_ready": orchestrator_ready,
    }
