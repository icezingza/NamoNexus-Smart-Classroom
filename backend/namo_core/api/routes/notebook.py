from fastapi import APIRouter, HTTPException, Body, Depends, Request, BackgroundTasks
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from namo_core.services.lessons.notebook_service import NotebookService
from namo_core.services.knowledge.tripitaka_retriever import search_tripitaka
from namo_core.database.core import SessionLocal
from namo_core.database.models import Teacher, NotebookJob

router = APIRouter(prefix="/notebook", tags=["notebook"])

# --- Dependencies ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_teacher(request: Request, db: Session = Depends(get_db)):
    username = getattr(request.state, "user", None)
    if not username:
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบ")
    
    teacher = db.query(Teacher).filter(Teacher.username == username).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลผู้ใช้")
    return teacher

# --- Models ---

class SourceItem(BaseModel):
    title: str
    text: str
    source: str = "custom"

class NotebookSaveRequest(BaseModel):
    id: Optional[int] = None
    title: str
    sources: List[SourceItem]

class NotebookGenerateRequest(BaseModel):
    notebook_id: Optional[int] = None
    sources: List[SourceItem]
    mode: str
    instruction: Optional[str] = ""

# --- Helper for Background Task ---

def run_generation_task(
    job_id: str, 
    teacher_id: int,
    notebook_id: Optional[int],
    sources: List[Dict],
    mode: str,
    instruction: str
):
    """ฟังก์ชันที่ทำงานใน Background เพื่อเรียก AI และบันทึกผล"""
    # สร้าง DB Session ใหม่สำหรับ thread นี้
    db = SessionLocal()
    try:
        service = NotebookService(db)
        
        # เลือกฟังก์ชันตามโหมด
        mode_map = {
            "briefing": service.generate_briefing_doc,
            "faq": service.generate_faq_study_guide,
            "audio": service.generate_audio_overview_script,
            "flashcard": service.generate_flashcards,
            "quiz": service.generate_quiz
        }
        
        gen_func = mode_map.get(mode)
        if not gen_func:
            service.update_job(job_id, "failed", error="Invalid mode")
            return

        # เรียก AI (Blocking call ใน thread นี้)
        result = gen_func(sources, instruction=instruction)
        
        if "error" in result:
            service.update_job(job_id, "failed", error=result["error"])
            return

        # บันทึกเนื้อหาที่สร้างได้
        content_id = None
        if notebook_id:
            content_obj = service.save_generated_content(
                notebook_id, mode, result["title"], result["content"], instruction
            )
            content_id = content_obj.id
            
        # อัปเดต Job ว่าเสร็จแล้ว
        service.update_job(job_id, "completed", content_id=content_id)
        
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(f"Generation job failed: {exc}")
        # อัปเดตสถานะว่าพัง
        # เราต้องสร้าง Service ใหม่เพราะอันเก่าอาจจะผูกกับ session ที่พัง
        db_err = SessionLocal()
        NotebookService(db_err).update_job(job_id, "failed", error=str(exc))
        db_err.close()
    finally:
        db.close()

# --- Endpoints ---

@router.get("/list")
def list_notebooks(db: Session = Depends(get_db), teacher: Teacher = Depends(get_current_teacher)):
    service = NotebookService(db)
    notebooks = service.list_teacher_notebooks(teacher.id)
    return [
        {"id": nb.id, "title": nb.title, "created_at": nb.created_at, "source_count": len(nb.sources)} 
        for nb in notebooks
    ]

@router.get("/job/{job_id}")
def get_job_status(job_id: str, db: Session = Depends(get_db), teacher: Teacher = Depends(get_current_teacher)):
    """เช็คสถานะงานที่รันอยู่ใน Background"""
    job = db.query(NotebookJob).filter(NotebookJob.id == job_id, NotebookJob.teacher_id == teacher.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.id,
        "status": job.status,
        "mode": job.mode,
        "content_id": job.result_content_id,
        "error": job.error_message,
        "created_at": job.created_at
    }

@router.post("/save")
def save_notebook(payload: NotebookSaveRequest, db: Session = Depends(get_db), teacher: Teacher = Depends(get_current_teacher)):
    service = NotebookService(db)
    sources_dict = [item.dict() for item in payload.sources]
    nb = service.save_notebook(teacher.id, payload.title, sources_dict, payload.id)
    return {"message": "บันทึกเรียบร้อย", "notebook_id": nb.id}

@router.post("/generate")
def generate_notebook_content(
    payload: NotebookGenerateRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), 
    teacher: Teacher = Depends(get_current_teacher)
):
    """
    สร้างเนื้อหาแบบ Asynchronous
    คืนค่า job_id ทันที และรัน AI ใน Background
    """
    service = NotebookService(db)
    
    # บันทึก Audit Log
    service.audit_log(teacher.id, "generate", payload.notebook_id, payload.instruction)
    
    # สร้าง Job Tracking
    job_id = service.create_job(teacher.id, payload.mode, payload.notebook_id)
    
    # สั่งรันงานใน Background
    background_tasks.add_task(
        run_generation_task,
        job_id,
        teacher.id,
        payload.notebook_id,
        [item.dict() for item in payload.sources],
        payload.mode,
        payload.instruction
    )
    
    return {
        "message": "กำลังประมวลผลข้อมูลในระบบหลังบ้าน",
        "job_id": job_id,
        "status": "pending"
    }

@router.get("/suggest-sources")
def suggest_sources(q: str):
    results = search_tripitaka(q, top_k=5)
    return {
        "suggestions": [
            {"title": r.get("title"), "text": r.get("text"), "source": "tripitaka"} for r in results
        ]
    }
