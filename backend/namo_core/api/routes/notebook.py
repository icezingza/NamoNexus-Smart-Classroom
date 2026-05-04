from fastapi import APIRouter, HTTPException, Body, Depends, Request, BackgroundTasks, WebSocket, WebSocketDisconnect, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import json
import asyncio
import logging
import redis.asyncio as redis

from namo_core.services.lessons.notebook_service import NotebookService
from namo_core.services.knowledge.tripitaka_retriever import search_tripitaka
from namo_core.services.knowledge.knowledge_service import KnowledgeService
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
    # Standard authentication from EnterpriseAuthMiddleware
    user_state = getattr(request.state, "user", None)
    if not user_state:
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบ")

    # Resolve username from state (string bypass or JWT dict payload)
    if isinstance(user_state, str):
        # Dev bypass tokens — use admin username
        from namo_core.config.settings import get_settings
        username = get_settings().admin_username
    elif isinstance(user_state, dict):
        username = user_state.get("sub", "")
    else:
        username = str(user_state)

    teacher = db.query(Teacher).filter(Teacher.username == username).first()
    if not teacher:
        # Auto-create teacher record on first use (dev/demo convenience)
        teacher = Teacher(username=username)
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
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
        
        # Publish event ผ่าน Redis แบบ Async (Phase 4 WebSocket Edition)
        from namo_core.config.settings import get_settings
        settings = get_settings()
        if settings.redis_url:
            async def _publish():
                try:
                    r = redis.Redis.from_url(settings.redis_url, decode_responses=True)
                    payload = json.dumps({
                        "status": "completed",
                        "job_id": job_id,
                        "title": result["title"],
                        "content": result["content"]
                    }, ensure_ascii=False)
                    await r.publish(f"notebook_events:{job_id}", payload)
                    # Cache the result temporarily with 1 hour TTL to avoid Race Conditions
                    await r.setex(f"notebook_job_cache:{job_id}", 3600, payload)
                    await r.aclose()
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Redis publish failed: {e}")
            
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(_publish())
                else:
                    asyncio.run(_publish())
            except Exception:
                asyncio.run(_publish())

    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(f"Generation job failed: {exc}")
        db_err = SessionLocal()
        NotebookService(db_err).update_job(job_id, "failed", error=str(exc))
        db_err.close()
        
        # Error Publish
        from namo_core.config.settings import get_settings
        settings = get_settings()
        if settings.redis_url:
            async def _publish_err():
                try:
                    r = redis.Redis.from_url(settings.redis_url, decode_responses=True)
                    payload = json.dumps({
                        "status": "failed",
                        "job_id": job_id,
                        "error": str(exc)
                    }, ensure_ascii=False)
                    await r.publish(f"notebook_events:{job_id}", payload)
                    await r.setex(f"notebook_job_cache:{job_id}", 3600, payload)
                    await r.aclose()
                except Exception:
                    pass
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(_publish_err())
                else:
                    asyncio.run(_publish_err())
            except Exception:
                asyncio.run(_publish_err())
    finally:
        db.close()

# --- Endpoints ---

@router.get("/list")
async def list_notebooks(db: Session = Depends(get_db), teacher: Teacher = Depends(get_current_teacher)):
    service = NotebookService(db)
    notebooks = await asyncio.to_thread(service.list_teacher_notebooks, teacher.id)
    return [
        {"id": nb.id, "title": nb.title, "created_at": nb.created_at, "source_count": len(nb.sources)}
        for nb in notebooks
    ]

@router.get("/job/{job_id}")
async def get_job_status(job_id: str, db: Session = Depends(get_db), teacher: Teacher = Depends(get_current_teacher)):
    """เช็คสถานะงานที่รันอยู่ใน Background"""
    job = await asyncio.to_thread(
        lambda: db.query(NotebookJob).filter(NotebookJob.id == job_id, NotebookJob.teacher_id == teacher.id).first()
    )
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
async def save_notebook(payload: NotebookSaveRequest, db: Session = Depends(get_db), teacher: Teacher = Depends(get_current_teacher)):
    service = NotebookService(db)
    sources_dict = [item.dict() for item in payload.sources]
    nb = await asyncio.to_thread(service.save_notebook, teacher.id, payload.title, sources_dict, payload.id)
    return {"message": "บันทึกเรียบร้อย", "notebook_id": nb.id}

@router.post("/generate")
async def generate_notebook_content(
    payload: NotebookGenerateRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), 
    teacher: Teacher = Depends(get_current_teacher)
):
    """
    สร้างเนื้อหา Notebook:
    - ถ้ามี Redis → Async Background + job_id (Real-time WebSocket)
    - ถ้าไม่มี Redis → Sync ใน thread แล้วคืนผลตรงๆ (LAN Demo Mode)
    """
    from namo_core.config.settings import get_settings
    settings = get_settings()
    service = NotebookService(db)
    service.audit_log(teacher.id, "generate", payload.notebook_id, payload.instruction)

    mode_map = {
        "briefing": service.generate_briefing_doc,
        "faq": service.generate_faq_study_guide,
        "audio": service.generate_audio_overview_script,
        "flashcard": service.generate_flashcards,
        "quiz": service.generate_quiz,
    }
    gen_func = mode_map.get(payload.mode)
    if not gen_func:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {payload.mode}")

    sources_dict = [item.dict() for item in payload.sources]

    if not settings.redis_url:
        # ══ LAN Demo Mode: Sync Generation (no Redis needed) ══
        import asyncio
        result = await asyncio.to_thread(gen_func, sources_dict, instruction=payload.instruction)
        return {
            "status": "completed",
            "title": result.get("title", ""),
            "content": result.get("content", ""),
            "source_count": result.get("source_count", len(sources_dict)),
        }

    # ══ Production Mode: Async Background + job_id ══
    job_id = service.create_job(teacher.id, payload.mode, payload.notebook_id)
    background_tasks.add_task(
        run_generation_task,
        job_id,
        teacher.id,
        payload.notebook_id,
        sources_dict,
        payload.mode,
        payload.instruction
    )
    return {
        "message": "กำลังประมวลผลข้อมูลในระบบหลังบ้าน",
        "job_id": job_id,
        "status": "pending"
    }

@router.get("/suggest-sources")
async def suggest_sources(
    q: str = Query(..., description="คำค้นหาสำหรับคัมภีร์", min_length=1, max_length=500),
    top_k: int = Query(5, description="จำนวนผลลัพธ์สูงสุด", ge=1, le=10),
) -> dict:
    """
    ค้นหาคัมภีร์จาก Tripitaka FAISS index เพื่อใช้เป็นแหล่งข้อมูลใน Notebook.
    ตอบกลับในรูปแบบที่ NotebookDashboard คาดหวัง ({ "suggestions": [...] })
    """
    # Use KnowledgeService so results include both Tripitaka AND global_library (23 books)
    ks = KnowledgeService()
    results = await asyncio.to_thread(ks.search, q, top_k)
    for r in results:
        if "source" not in r:
            r["source"] = "tripitaka"
    return {"suggestions": results}

@router.websocket("/ws/{job_id}")
async def websocket_job_status(websocket: WebSocket, job_id: str):
    """
    WebSocket Endpoint for real-time Notebook Job status updates.
    Prevents race conditions by checking cache/DB first, then subscribing to Redis PubSub.
    Falls back to polling if Redis is not available.
    """
    await websocket.accept()
    from namo_core.config.settings import get_settings
    settings = get_settings()

    # Fallback: If Redis not configured, poll the database
    if not settings.redis_url:
        import asyncio
        try:
            # Poll database for job completion (max 5 minutes)
            for attempt in range(150):  # 150 * 2 seconds = 300 seconds = 5 minutes
                await asyncio.sleep(2)
                db = SessionLocal()
                try:
                    job = db.query(NotebookJob).filter(NotebookJob.id == job_id).first()
                    if job and job.status != "pending":
                        if job.status == "failed":
                            await websocket.send_text(json.dumps({"status": "failed", "error": job.error_message}))
                        elif job.status == "completed" and job.result_content_id:
                            from namo_core.database.models import NotebookContent
                            content = db.query(NotebookContent).filter(NotebookContent.id == job.result_content_id).first()
                            if content:
                                await websocket.send_text(json.dumps({
                                    "status": "completed",
                                    "job_id": job_id,
                                    "title": content.title,
                                    "content": content.content
                                }, ensure_ascii=False))
                        await websocket.close()
                        return
                finally:
                    db.close()
        except Exception as e:
            logging.getLogger(__name__).error(f"WebSocket polling fallback failed: {e}")
            await websocket.close()
        return

    r = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        # 1. Race Condition Check: Check Cache first
        cached = await r.get(f"notebook_job_cache:{job_id}")
        if cached:
            await websocket.send_text(cached)
            await websocket.close()
            return
            
        # 2. Race Condition Check: Check DB
        db = SessionLocal()
        try:
            job = db.query(NotebookJob).filter(NotebookJob.id == job_id).first()
            if job and job.status != "pending":
                if job.status == "failed":
                    await websocket.send_text(json.dumps({"status": "failed", "error": job.error_message}))
                elif job.status == "completed" and job.result_content_id:
                    from namo_core.database.models import NotebookContent
                    content = db.query(NotebookContent).filter(NotebookContent.id == job.result_content_id).first()
                    if content:
                        await websocket.send_text(json.dumps({
                            "status": "completed",
                            "job_id": job_id,
                            "title": content.title,
                            "content": content.content
                        }, ensure_ascii=False))
                await websocket.close()
                return
        finally:
            db.close()
            
        # 3. Subscribe to Redis PubSub
        pubsub = r.pubsub()
        await pubsub.subscribe(f"notebook_events:{job_id}")
        
        async def _listen_pubsub():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    payload = message["data"]
                    await websocket.send_text(payload)
                    await websocket.close()
                    break

        async def _check_disconnect():
            try:
                while True:
                    # Receive text is a keep-alive/disconnect detection
                    msg = await websocket.receive_text()
                    if msg.strip() == "ping":
                        await websocket.send_text("pong")
            except WebSocketDisconnect:
                pass
                
        listen_task = asyncio.create_task(_listen_pubsub())
        disconnect_task = asyncio.create_task(_check_disconnect())
        
        await asyncio.wait(
            [listen_task, disconnect_task], 
            return_when=asyncio.FIRST_COMPLETED
        )
        
    except WebSocketDisconnect:
        pass
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"WebSocket error: {e}")
    finally:
        await r.aclose()
