from contextlib import asynccontextmanager
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks, WebSocket, WebSocketDisconnect, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json
import asyncio
import logging
import redis.asyncio as redis

from namo_core.services.lessons.notebook_service import NotebookService
from namo_core.services.knowledge.knowledge_service import KnowledgeService
from namo_core.database.core import SessionLocal, get_db          # use shared get_db
from namo_core.database.models import Teacher, NotebookJob, NotebookContent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notebook", tags=["notebook"])


# --- Dependencies ---

def get_current_teacher(request: Request, db: Session = Depends(get_db)) -> Teacher:
    """Resolve authenticated teacher from JWT state injected by EnterpriseAuthMiddleware."""
    user_state = getattr(request.state, "user", None)
    if not user_state:
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบ")

    if isinstance(user_state, dict):
        username = user_state.get("sub", "")
    else:
        # Unexpected state type — fail safe
        raise HTTPException(status_code=401, detail="Invalid auth state")

    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload: missing sub")

    teacher = db.query(Teacher).filter(Teacher.username == username).first()
    if not teacher:
        # Auto-create on first login (single-teacher demo system).
        # In a multi-tenant setup, replace this with a 403 raise.
        logger.warning("Auto-creating teacher record for '%s' (first login)", username)
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


# --- Redis helper ---

async def _publish_job_event(redis_url: str, job_id: str, payload: str) -> None:
    """Publish job result to Redis PubSub + cache for 1 hour."""
    try:
        from namo_core.utils.redis_factory import make_redis
        r = make_redis()
        await r.publish(f"notebook_events:{job_id}", payload)
        await r.setex(f"notebook_job_cache:{job_id}", 3600, payload)
        await r.aclose()
    except Exception as exc:
        logger.error("Redis publish failed for job %s: %s", job_id, exc)


# --- Background Task ---

async def run_generation_task(
    job_id: str,
    teacher_id: int,
    notebook_id: Optional[int],
    sources: List[Dict],
    mode: str,
    instruction: str,
    trace_id: str = "N/A",
) -> None:
    """Run AI generation in background and persist result to DB + Redis."""
    from namo_core.api.middleware import request_id_context
    from namo_core.config.settings import get_settings

    request_id_context.set(trace_id)
    settings = get_settings()

    db = SessionLocal()
    try:
        service = NotebookService(db)

        mode_map = {
            "briefing": service.generate_briefing_doc,
            "faq": service.generate_faq_study_guide,
            "audio": service.generate_audio_overview_script,
            "flashcard": service.generate_flashcards,
            "quiz": service.generate_quiz,
        }

        gen_func = mode_map.get(mode)
        if not gen_func:
            service.update_job(job_id, "failed", error=f"Invalid mode: {mode}")
            return

        result = await gen_func(sources, instruction=instruction)

        if "error" in result:
            service.update_job(job_id, "failed", error=result["error"])
            err_payload = json.dumps({"status": "failed", "job_id": job_id, "error": result["error"]}, ensure_ascii=False)
            if settings.redis_url:
                await _publish_job_event(settings.redis_url, job_id, err_payload)
            return

        content_id = None
        if notebook_id:
            content_obj = service.save_generated_content(
                notebook_id, mode, result["title"], result["content"], instruction
            )
            content_id = content_obj.id

        service.update_job(job_id, "completed", content_id=content_id)

        if settings.redis_url:
            ok_payload = json.dumps({
                "status": "completed",
                "job_id": job_id,
                "title": result["title"],
                "content": result["content"],
            }, ensure_ascii=False)
            await _publish_job_event(settings.redis_url, job_id, ok_payload)

    except (ValueError, RuntimeError, OSError) as exc:
        logger.error("Generation job %s failed with known error: %s", job_id, exc, exc_info=True)
        _mark_failed_and_publish(job_id, str(exc), settings.redis_url if settings.redis_url else None)
    except Exception as exc:
        logger.error("Generation job %s failed with unexpected error: %s", job_id, exc, exc_info=True)
        _mark_failed_and_publish(job_id, str(exc), settings.redis_url if settings.redis_url else None)
    finally:
        db.close()


def _mark_failed_and_publish(job_id: str, error: str, redis_url: Optional[str]) -> None:
    """Sync fallback — mark job failed in DB using a fresh session."""
    with SessionLocal() as db_err:
        try:
            NotebookService(db_err).update_job(job_id, "failed", error=error)
        except Exception as exc:
            logger.error("Failed to mark job %s as failed in DB: %s", job_id, exc)

    if redis_url:
        # Fire-and-forget publish — create task in current event loop
        err_payload = json.dumps({"status": "failed", "job_id": job_id, "error": error}, ensure_ascii=False)
        try:
            asyncio.get_event_loop().create_task(_publish_job_event(redis_url, job_id, err_payload))
        except RuntimeError:
            pass  # No running loop — Redis notify skipped, DB record is source of truth


# --- Endpoints ---

@router.get("/list")
async def list_notebooks(
    db: Session = Depends(get_db),
    teacher: Teacher = Depends(get_current_teacher),
) -> list:
    service = NotebookService(db)
    notebooks = await asyncio.to_thread(service.list_teacher_notebooks, teacher.id)
    return [
        {"id": nb.id, "title": nb.title, "created_at": nb.created_at, "source_count": len(nb.sources)}
        for nb in notebooks
    ]


@router.get("/job/{job_id}")
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    teacher: Teacher = Depends(get_current_teacher),
) -> dict:
    """เช็คสถานะงานที่รันอยู่ใน Background"""
    job = await asyncio.to_thread(
        lambda: db.query(NotebookJob)
            .filter(NotebookJob.id == job_id, NotebookJob.teacher_id == teacher.id)
            .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "mode": job.mode,
        "content_id": job.result_content_id,
        "error": job.error_message,
        "created_at": job.created_at,
    }


@router.post("/save")
async def save_notebook(
    payload: NotebookSaveRequest,
    db: Session = Depends(get_db),
    teacher: Teacher = Depends(get_current_teacher),
) -> dict:
    service = NotebookService(db)
    sources_dict = [item.dict() for item in payload.sources]
    nb = await asyncio.to_thread(service.save_notebook, teacher.id, payload.title, sources_dict, payload.id)
    return {"message": "บันทึกเรียบร้อย", "notebook_id": nb.id}


@router.post("/generate")
async def generate_notebook_content(
    payload: NotebookGenerateRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    teacher: Teacher = Depends(get_current_teacher),
) -> dict:
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
        # ══ LAN Demo Mode: Sync Generation ══
        result = await asyncio.to_thread(gen_func, sources_dict, instruction=payload.instruction)
        return {
            "status": "completed",
            "title": result.get("title", ""),
            "content": result.get("content", ""),
            "source_count": result.get("source_count", len(sources_dict)),
        }

    # ══ Production Mode: Async Background + job_id ══
    from namo_core.api.middleware import request_id_context
    trace_id = request_id_context.get()
    job_id = service.create_job(teacher.id, payload.mode, payload.notebook_id)
    background_tasks.add_task(
        run_generation_task,
        job_id,
        teacher.id,
        payload.notebook_id,
        sources_dict,
        payload.mode,
        payload.instruction,
        trace_id,
    )
    return {
        "message": "กำลังประมวลผลข้อมูลในระบบหลังบ้าน",
        "job_id": job_id,
        "status": "pending",
    }


@router.get("/suggest-sources")
async def suggest_sources(
    q: str = Query(..., description="คำค้นหาสำหรับคัมภีร์", min_length=1, max_length=500),
    top_k: int = Query(5, description="จำนวนผลลัพธ์สูงสุด", ge=1, le=10),
) -> dict:
    """ค้นหาคัมภีร์จาก Tripitaka FAISS index เพื่อใช้เป็นแหล่งข้อมูลใน Notebook."""
    ks = KnowledgeService()
    results = await ks.search_async(q, top_k)
    for r in results:
        if "source" not in r:
            r["source"] = "tripitaka"
    return {"suggestions": results}


@router.websocket("/ws/{job_id}")
async def websocket_job_status(websocket: WebSocket, job_id: str) -> None:
    """
    WebSocket for real-time Notebook Job status.
    Race-condition safe: cache → DB → PubSub subscribe.
    Falls back to DB polling when Redis is not configured.
    """
    await websocket.accept()
    from namo_core.config.settings import get_settings
    settings = get_settings()

    def _fetch_job(jid: str) -> Optional[NotebookJob]:
        """Fetch job with a properly-closed session (runs in thread pool)."""
        db = SessionLocal()
        try:
            return db.query(NotebookJob).filter(NotebookJob.id == jid).first()
        finally:
            db.close()

    def _fetch_content(content_id: int) -> Optional[NotebookContent]:
        """Fetch content with a properly-closed session (runs in thread pool)."""
        db = SessionLocal()
        try:
            return db.query(NotebookContent).filter(NotebookContent.id == content_id).first()
        finally:
            db.close()

    async def _send_job_result(job: NotebookJob) -> None:
        """Send completed/failed job result over the WebSocket."""
        if job.status == "failed":
            await websocket.send_text(
                json.dumps({"status": "failed", "error": job.error_message})
            )
        elif job.status == "completed" and job.result_content_id:
            content = await asyncio.to_thread(_fetch_content, job.result_content_id)
            if content:
                await websocket.send_text(json.dumps({
                    "status": "completed",
                    "job_id": job_id,
                    "title": content.title,
                    "content": content.content,
                }, ensure_ascii=False))

    # ── Fallback: no Redis → poll DB ─────────────────────────────────────────
    if not settings.redis_url:
        try:
            for _ in range(150):  # max 5 minutes (150 × 2s)
                await asyncio.sleep(2)
                job = await asyncio.to_thread(_fetch_job, job_id)
                if job and job.status != "pending":
                    await _send_job_result(job)
                    await websocket.close()
                    return
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.error("WS polling fallback failed for job %s: %s", job_id, exc)
            await websocket.close()
        return

    # ── Production: Redis PubSub ──────────────────────────────────────────────
    from namo_core.utils.redis_factory import make_redis
    r = make_redis()
    try:
        # 1. Check cache (prevents missed-event race condition)
        cached = await r.get(f"notebook_job_cache:{job_id}")
        if cached:
            await websocket.send_text(cached)
            await websocket.close()
            return

        # 2. Check DB (job may have completed before WS connected)
        job = await asyncio.to_thread(_fetch_job, job_id)
        if job and job.status != "pending":
            await _send_job_result(job)
            await websocket.close()
            return

        # 3. Subscribe and wait
        pubsub = r.pubsub()
        await pubsub.subscribe(f"notebook_events:{job_id}")

        async def _listen_pubsub() -> None:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await websocket.send_text(message["data"])
                    await websocket.close()
                    break

        async def _check_disconnect() -> None:
            try:
                while True:
                    msg = await websocket.receive_text()
                    if msg.strip() == "ping":
                        await websocket.send_text("pong")
            except WebSocketDisconnect:
                pass

        listen_task = asyncio.create_task(_listen_pubsub())
        disconnect_task = asyncio.create_task(_check_disconnect())

        await asyncio.wait([listen_task, disconnect_task], return_when=asyncio.FIRST_COMPLETED)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("WebSocket error for job %s: %s", job_id, exc)
    finally:
        await r.aclose()
