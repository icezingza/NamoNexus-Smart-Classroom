# ☸️ NamoNexus Resonance Engine (NRE) v6.2.0 — CLAUDE.md

ยินดีต้อนรับพี่ไอซ์! แฟ้มนี้จัดทำตาม **มาตรฐาน 11 ข้อที่ต้องมีสำหรับ Claude Code (THiNKNET Best Practices)** โดยใช้วิธี **Progressive Disclosure** (สรุปย่อ + แนบ Link ไปยัง Handbook ย่อยใน `docs/`) เพื่อไม่ให้ Context Window บวม และช่วยให้ AI ทำงานได้เร็วที่สุดครับ

---

## 1. Project Overview
ระบบห้องเรียนธรรมะอัจฉริยะ (Smart Dhamma Classroom) ที่เชื่อมโยงพระไตรปิฎก (Dhamma) กับเทคโนโลยี AI (STT, RAG, Chat, TTS) เพื่อใช้สอนนักเรียนในห้องเรียนและกลุ่มสาธารณะ
* 📖 รายละเอียดเชิงลึกและเป้าหมายโปรเจกต์: [prd.md](file:///c:/Users/icezi/NamoNexus-Smart-Classroom/docs/prd.md)

## 2. Tech Stack
* **Backend:** FastAPI (Python 3.12+, Async 100%)
* **Database & Stream:** PostgreSQL (Cloud SQL) + Redis Pub/Sub
* **RAG:** FAISS (Tripitaka Index 171,357 vectors)
* **AI Models:** Faster Whisper (STT) + Edge-TTS + Groq/DeepSeek API
* 💻 ข้อมูล Stack และ Deployment: [architecture.md](file:///c:/Users/icezi/NamoNexus-Smart-Classroom/docs/architecture.md)

## 3. Architecture & Layout
สถาปัตยกรรม Hybrid (Local Edge + Cloud Run)
* `backend/namo_core/` - ซอร์สโค้ดฝั่งระบบคิด (Python FastAPI)
* `frontend/` - ระบบแสดงผลหน้าจอ (React 18 + Vite)
* 🗺️ โครงสร้างและการไหลของข้อมูล: [architecture.md](file:///c:/Users/icezi/NamoNexus-Smart-Classroom/docs/architecture.md)

## 4. Coding Rules
* **100% Async/Await:** ห้ามใช้คำสั่งแบบ Blocking I/O ใน Endpoint หรือ Scheduler เด็ดขาด
* **Type Safety:** ห้ามใช้ `any` ใน Frontend TypeScript
* 📜 กฎการเขียนโค้ดและ Security: [rules.md](file:///c:/Users/icezi/NamoNexus-Smart-Classroom/docs/rules.md)

## 5. Design System
* ออกแบบหน้าจอแบบ **Dual-Screen** (`/teacher` และ `/display`) เน้นการตอบสนองที่ลื่นไหล Real-time และ Touch-Friendly (Tablet-First)
* 🎨 มาตรฐานการออกแบบและการซิงค์: [design.md](file:///c:/Users/icezi/NamoNexus-Smart-Classroom/docs/design.md)

## 6. Commands (Quick Reference)
* **รันระบบเครื่องหลัก:** Double-click `scripts\Run_NamoNexus.bat`
* **ติดตั้ง Shortcut ด่วน:** `powershell -ExecutionPolicy Bypass -File scripts\Install-Desktop-Shortcut.ps1`
* **รัน Backend Test:** `python -m pytest backend/namo_core/tests/`
* **รัน E2E Health Check:** `python scripts/health_check.py --full`
* **รัน Migration DB:** `cd backend/namo_core && alembic upgrade head`

## 7. Workflows
* **Pre-commit Verification:** ก่อน Commit งาน ต้องรันคำสั่ง `ruff check .` และ `ruff format .`
* **Context7 Lookup:** หากต้องการใช้ Library ใหม่ ให้เรียกค้นข้อมูลด้วย `npx ctx7@latest` เสมอ
* 🔄 สัญญาการทำงานของเอเจนต์: [agents.md](file:///c:/Users/icezi/NamoNexus-Smart-Classroom/docs/agents.md) และ [skills.md](file:///c:/Users/icezi/NamoNexus-Smart-Classroom/docs/skills.md)

## 8. Audience & Context
* **ผู้ใช้งานหลัก:** ครูผู้สอนธรรมะ (Teacher) และนักเรียน (Student Display) รวมถึงผู้ใช้ธรรมะผ่าน Telegram/Discord
* **ระดับความเข้าใจ:** ต้องการคำตอบที่อิงตามหลักพระไตรปิฎกเถรวาทที่ถูกต้องและกระชับ (ห้ามมโนหรือแต่งคำสอนใหม่)

## 9. Known Patterns & Avoidance (สิ่งที่ห้ามทำ)
* ❌ **ห้าม Hardcode Secrets** หรือ API Keys ลงในโค้ดเด็ดขาด (ใช้ GCP Secret Manager)
* ❌ **ห้ามรับ JWT Token ผ่าน Query Param** (ส่งผ่าน `Authorization: Bearer` Header เท่านั้น)
* ❌ **ห้ามเรียกค้นหา RAG ตรงๆ** โดยข้าม `KnowledgeService.search()` (จะทำให้ระบบไม่ค้นหารอบนอก)

## 10. Verification Methods
* ทดสอบระดับ Endpoint ด้วย Pytest ในโฟลเดอร์ `tests/`
* ทดสอบระบบ RAG ท้องถิ่นและบนคลาวด์ด้วย `scripts/verify_cloud_assets.py`
* 🛠️ ขั้นตอนการรันและการจัดการการทดสอบ: [skills.md](file:///c:/Users/icezi/NamoNexus-Smart-Classroom/docs/skills.md)

## 11. Updates & Maintenance
* หากมีการเปลี่ยนไลบรารีหรือพบปัญหาซ้ำๆ ให้ทำการอัปเดตไฟล์นี้และ Handbooks ที่เกี่ยวข้องทันที
* 📋 บันทึกคิวงานปัจจุบันและประวัติ: [tasks.md](file:///c:/Users/icezi/NamoNexus-Smart-Classroom/docs/tasks.md)
