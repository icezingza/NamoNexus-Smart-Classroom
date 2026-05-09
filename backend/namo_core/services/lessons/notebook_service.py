"""
NotebookService — Source-grounded content synthesis inspired by NotebookLM.
Provides tools for teachers to create briefing docs, FAQs, and study guides
strictly from provided sources.
"""

import httpx
import logging
import re
import asyncio
from typing import List, Dict, Any, Optional
import tiktoken

from namo_core.services.knowledge.knowledge_service import ContextBuilder
from namo_core.config.settings import get_settings

from sqlalchemy.orm import Session
from namo_core.database.models import Notebook, NotebookSource, NotebookContent, Teacher, NotebookAuditLog, NotebookJob

logger = logging.getLogger(__name__)

class NotebookService:
    def __init__(self, db: Session = None):
        self.db = db
        self.context_builder = ContextBuilder()
        self._encoding = tiktoken.get_encoding("cl100k_base") # Standard for GPT-4/Llama-3 tokenization

    async def _call_groq_async(self, prompt: str) -> str:
        """เรียก Groq API แบบ Asynchronous ป้องกันการบล็อก Thread Pool"""
        settings = get_settings()
        api_key = settings.reasoning_api_key.strip() if settings.reasoning_api_key else None
        base_url = settings.reasoning_api_base_url or "https://api.groq.com/openai/v1"
        model = settings.reasoning_model or "llama-3.3-70b-versatile"
        timeout = settings.reasoning_timeout_seconds or 60.0

        if not api_key:
            logger.warning("No API key configured, returning mock response")
            return f"[Mock Response] ไม่มี API Key กรุณาตั้งค่า NAMO_REASONING_API_KEY ใน .env"

        from namo_core.api.middleware import request_id_context
        trace_id = request_id_context.get()

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}".strip(),
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
        except httpx.TimeoutException:
            logger.error("[%s] Groq API timed out after %s seconds", trace_id, timeout)
            return f"[Error] Groq API ตอบกลับช้าเกินไป (Timeout {timeout}s)"
        except Exception as exc:
            logger.error("[%s] Groq API call failed: %s", trace_id, exc)
            return f"[Error] เกิดข้อผิดพลาด: {exc}"

    def audit_log(self, teacher_id: int, action: str, notebook_id: int = None, instruction: str = None, ip: str = None):
        """บันทึกประวัติการใช้งานเพื่อความปลอดภัย"""
        if not self.db: return
        log = NotebookAuditLog(
            teacher_id=teacher_id,
            action=action,
            notebook_id=notebook_id,
            instruction_sanitized=instruction[:500] if instruction else None,
            ip_address=ip
        )
        self.db.add(log)
        self.db.commit()

    def _validate_instruction(self, instruction: str) -> str:
        """ตรวจสอบและกรองคำสั่งที่เป็นอันตราย (Prompt Injection Guard)"""
        if not instruction: return ""
        
        # กรอง Keyword ที่อันตราย
        forbidden_patterns = [
            r"ignore\s+all", r"system\s+prompt", r"dump\s+database", 
            r"delete", r"drop\s+table", r"reveal\s+secret"
        ]
        
        sanitized = instruction
        for pattern in forbidden_patterns:
            if re.search(pattern, instruction, re.IGNORECASE):
                logger.warning(f"Malicious instruction detected: {instruction}")
                return "[REDACTED - Malicious Instruction Blocked]"
        
        return sanitized

    def _calculate_tokens(self, text: str) -> int:
        """นับ Token แม่นยำโดยใช้ tiktoken (Sovereign Edition)"""
        return len(self._encoding.encode(text))

    def _get_context_with_limit(self, sources: List[Dict], limit: int = 6000) -> str:
        """สร้าง Context โดยควบคุมไม่ให้เกิน Token Limit"""
        context = ""
        for i, src in enumerate(sources):
            chunk = f"\n[{i+1}] {src.get('title')}\n{src.get('text')}\n---"
            if self._calculate_tokens(context + chunk) > limit:
                logger.warning(f"Context limit reached ({limit} tokens). Truncating sources.")
                break
            context += chunk
        return context

    def list_teacher_notebooks(self, teacher_id: int):
        self.audit_log(teacher_id, "list")
        return self.db.query(Notebook).filter(Notebook.teacher_id == teacher_id).all()

    def get_notebook(self, notebook_id: int, teacher_id: int):
        self.audit_log(teacher_id, "view", notebook_id)
        return self.db.query(Notebook).filter(
            Notebook.id == notebook_id, 
            Notebook.teacher_id == teacher_id
        ).first()

    def save_notebook(self, teacher_id: int, title: str, sources: List[Dict], notebook_id: int = None):
        """สร้างหรืออัปเดตสมุดบันทึกและแหล่งข้อมูล"""
        self.audit_log(teacher_id, "save", notebook_id)
        
        if notebook_id:
            notebook = self.get_notebook(notebook_id, teacher_id)
            if not notebook:
                return None
            notebook.title = title
            self.db.query(NotebookSource).filter(NotebookSource.notebook_id == notebook_id).delete()
        else:
            notebook = Notebook(teacher_id=teacher_id, title=title)
            self.db.add(notebook)
            self.db.flush()

        for src in sources:
            source_obj = NotebookSource(
                notebook_id=notebook.id,
                title=src.get("title"),
                text=src.get("text"),
                source_type=src.get("source", "custom")
            )
            self.db.add(source_obj)
        
        self.db.commit()
        return notebook

    def create_job(self, teacher_id: int, mode: str, notebook_id: int = None) -> str:
        """สร้าง Job ID (UUID) สำหรับการประมวลผล Background"""
        import uuid
        job_id = str(uuid.uuid4())
        job = NotebookJob(
            id=job_id,
            teacher_id=teacher_id,
            notebook_id=notebook_id,
            mode=mode,
            status="pending"
        )
        self.db.add(job)
        self.db.commit()
        return job_id

    def update_job(self, job_id: str, status: str, content_id: int = None, error: str = None):
        """อัปเดตสถานะงาน"""
        job = self.db.query(NotebookJob).filter(NotebookJob.id == job_id).first()
        if job:
            job.status = status
            job.result_content_id = content_id
            job.error_message = error
            self.db.commit()

    def cleanup_stale_jobs(self, hours: int = 1):
        """ล้างงานที่ค้างอยู่ในสถานะ pending นานเกินไป (Recovery Mechanism)"""
        from datetime import datetime, timedelta, timezone
        threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
        stale_jobs = self.db.query(NotebookJob).filter(
            NotebookJob.status == "pending",
            NotebookJob.created_at <= threshold
        ).all()
        
        for job in stale_jobs:
            job.status = "failed"
            job.error_message = f"Job timed out (Stale for > {hours}h)"
            logger.info(f"Marking job {job.id} as failed (stale)")
        
        if stale_jobs:
            self.db.commit()
            return len(stale_jobs)
        return 0

    def save_generated_content(self, notebook_id: int, mode: str, title: str, content: str, instruction: str = ""):
        content_obj = NotebookContent(
            notebook_id=notebook_id,
            mode=mode,
            title=title,
            content=content,
            instruction_used=instruction
        )
        self.db.add(content_obj)
        self.db.commit()
        return content_obj

    async def generate_briefing_doc(self, sources: List[Dict[str, Any]], instruction: str = "") -> Dict[str, Any]:
        instr = self._validate_instruction(instruction)
        context = self._get_context_with_limit(sources)

        prompt = (
            "คุณคือผู้ช่วยอัจฉริยะสำหรับคุณครูสอนธรรมะ (Dhamma Teacher Assistant).\n"
            "ภารกิจของคุณคือสร้าง 'เอกสารสรุปเตรียมสอน (Briefing Doc)' โดยอ้างอิงจากแหล่งข้อมูลที่ให้มาเท่านั้น\n\n"
            f"คำสั่งพิเศษจากคุณครู: {instr if instr else 'ไม่มี'}\n\n"
            "โครงสร้างเอกสารประกอบด้วย:\n"
            "1. ใจความสำคัญ (Key Themes)\n"
            "2. สรุปเนื้อหาแบ่งตามหัวข้อ (Summary by Topics)\n"
            "3. คำศัพท์สำคัญหรือข้อธรรมที่ควรเน้น (Key Terms/Dhamma Concepts)\n"
            "4. แนวทางการนำไปประยุกต์สอนเด็ก (Teaching Tips)\n\n"
            "--- แหล่งข้อมูล ---\n"
            f"{context}\n"
            "------------------\n"
        )
        content = await self._call_groq_async(prompt)
        return {"title": "Briefing Doc", "content": content, "source_count": len(sources)}

    async def generate_faq_study_guide(self, sources: List[Dict[str, Any]], instruction: str = "") -> Dict[str, Any]:
        instr = self._validate_instruction(instruction)
        context = self._get_context_with_limit(sources)
        prompt = (
            "จงสร้าง 'คู่มือการเรียนรู้และรายการคำถาม-คำตอบ (Study Guide & FAQ)' จากแหล่งข้อมูลที่ให้มาเท่านั้น\n\n"
            f"คำสั่งพิเศษจากคุณครู: {instr if instr else 'ไม่มี'}\n\n"
            "ประกอบด้วย:\n"
            "1. คำถามที่พบบ่อย (FAQ)\n2. แบบฝึกหัด 3-5 ข้อ\n3. หัวข้อชวนคิด\n\n"
            "--- แหล่งข้อมูล ---\n"
            f"{context}\n"
        )
        content = await self._call_groq_async(prompt)
        return {"title": "Study Guide & FAQ", "content": content, "source_count": len(sources)}

    async def generate_audio_overview_script(self, sources: List[Dict[str, Any]], instruction: str = "") -> Dict[str, Any]:
        instr = self._validate_instruction(instruction)
        context = self._get_context_with_limit(sources)
        prompt = (
            "จงสร้าง 'บทสนทนาเจาะลึกธรรมะ (Dhamma Deep Dive)' สำหรับผู้พูด 2 คน: [ครูนาโม] และ [น้องแก้ว]\n"
            f"คำสั่งพิเศษ: {instr}\n\n"
            f"--- แหล่งข้อมูล ---\n{context}\n"
        )
        content = await self._call_groq_async(prompt)
        return {"title": "Audio Overview Script", "content": content, "source_count": len(sources)}

    async def generate_flashcards(self, sources: List[Dict[str, Any]], instruction: str = "") -> Dict[str, Any]:
        instr = self._validate_instruction(instruction)
        context = self._get_context_with_limit(sources)
        prompt = (
            "จงสร้าง 'Flashcards' จากแหล่งข้อมูลเท่านั้น\n"
            f"คำสั่งพิเศษ: {instr}\n\n"
            "รูปแบบ:\nFlashcard #[ตัวเลข]\nด้านหน้า: [คำถาม]\nด้านหลัง: [คำตอบ]\n\n"
            f"--- แหล่งข้อมูล ---\n{context}\n"
        )
        content = await self._call_groq_async(prompt)
        return {"title": "Flashcards", "content": content, "source_count": len(sources)}

    async def generate_quiz(self, sources: List[Dict[str, Any]], instruction: str = "") -> Dict[str, Any]:
        instr = self._validate_instruction(instruction)
        context = self._get_context_with_limit(sources)
        prompt = (
            "จงสร้าง 'แบบทดสอบ (Quiz)' จากแหล่งข้อมูลเท่านั้น\n"
            f"คำสั่งพิเศษ: {instr}\n\n"
            "รูปแบบ:\nข้อที่ [ตัวเลข]: [โจทย์]\nก) ... ข) ... ค) ... ง) ...\nเฉลย: [คำตอบ] เพราะ [เหตุผล]\n\n"
            f"--- แหล่งข้อมูล ---\n{context}\n"
        )
        content = await self._call_groq_async(prompt)
        return {"title": "Quiz", "content": content, "source_count": len(sources)}

