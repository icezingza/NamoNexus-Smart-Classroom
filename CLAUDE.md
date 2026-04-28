# ☸️ NamoNexus Resonance Engine (NRE) v5.0.0 — Sovereign Edition

## 1. Project Mental Model
"Infrastructure แห่งปัญญา" ที่เปลี่ยนพระไตรปิฎกให้กลายเป็นระบบห้องเรียนธรรมะอัจฉริยะ (Smart Dhamma Classroom) ผ่านสถาปัตยกรรม Hybrid (Local Edge + Public Cloud)

- Legacy reference เดิมของระบบยังอ้าง `162,895 vectors` ในหลายจุด [cite: 2026-04-17, 2026-04-21]
- Audit ล่าสุดของ production metadata ชุด `knowledge/tripitaka_main/tripitaka_metadata.json` พบ `168,861` chunk-level records [cite: 2026-04-27]
- แกนความรู้เล่ม 25 ยังเป็นจุดตั้งต้นสำคัญของ pipeline บางชุด แต่ production corpus ปัจจุบันใหญ่กว่าตัวเลข legacy แล้ว [cite: 2026-04-27]

## 2. Roles & Identity
- นะโม (Namo): AI Thinking Partner (Gen Z Professional, Blunt, No Fluff) [cite: 2026-02-03]
- พี่ไอซ์ (P'Ice): Tech Monk & AI Architect (Project Owner)
- Claude Code: Senior AI Software Engineer (Backend/Frontend/DevOps)

## 3. Tech Stack: Cloud-Native & Deep Async

### Backend (Lenovo Workstation / Edge Server)
- FastAPI (Async 100%): รองรับ concurrency สูงด้วย `asyncio.to_thread` และ `aiofiles` [cite: 2026-04-22, 2026-04-27]
- Knowledge Base: FAISS (ประมาณ 239 MB) + RAG Pipeline โดย FAISS index ปัจจุบันที่ `knowledge/tripitaka_main/tripitaka_index.faiss` มี `168,861` vectors (dim `384`); ตัวเลข `162,895` ให้ถือเป็น legacy reference ในเอกสารเก่า [cite: 2026-04-27]
- Persistent Layer: โค้ดปัจจุบันยังมี `SQLite` เป็น default fallback, มี Redis integration ใช้งานในหลาย service และมี PostgreSQL/Cloud SQL path สำหรับ cloud rollout [cite: 2026-04-27]

### Frontend (`namonexus.com`)
- React 18 + Vite: จัดการเส้นทางแบบ Dual-Screen (`/teacher` และ `/display`) [cite: 2026-04-27]
- Local frontend networking ใช้ `vite.config.ts` แบบ `host: true` และ resolve local host จาก `window.location.hostname` ใน browser runtime; ค่า `192.168.0.107` ให้ถือเป็น historical fallback เท่านั้น [cite: 2026-04-27]
- Real-time Stream: WebSockets + Redis Pub/Sub สำหรับ push ข้อมูลข้ามหน้าจอ (Latency < 50ms) [cite: 2026-04-27]

### Cloud Infrastructure (GCP) — SMART Pillar Storage
- **Bucket: `namo-classroom-models`**: (The Brain) เก็บ FAISS Index และ AI Models ที่ผ่านการเทรนแล้ว [cite: 2026-04-28]
- **Bucket: `namonexus-wisdom-storage`**: (The Knowledge Base) เก็บ Chunks พระไตรปิฎก 168,861 รายการ สำหรับ RAG [cite: 2026-04-28]
- **Bucket: `namo-classroom`**: (General Assets) เก็บไฟล์สื่อ, โลโก้ และ Frontend Assets [cite: 2026-04-28]
- Secret Manager: บริหารจัดการ API Keys ผ่าน `backend/namo_core/config/gcp_secrets.py` [cite: 2026-04-28]

## 4. Knowledge Quality & Automation
- Audit script: `scripts/audit_knowledge_vectors.py` [cite: 2026-04-27]
- **Batch Vectorizer**: `scripts/batch_vectorizer.py` (Auto-pilot สำหรับเปลี่ยน JSON Books เป็น FAISS Index ทีละเล่ม) [cite: 2026-04-28]
- Reusable filter module: `scripts/tripitaka_quality_filter.py` [cite: 2026-04-27]
- Ingestion entrypoint updated: `scripts/master_ingestion.py` now supports Hard/Soft filter pre-processing and `--dry-run` [cite: 2026-04-27]

### Latest Audit Snapshot (`2026-04-27`)
- Total chunk records: `168,861`
- Average chunk length: `619.25` characters
- Empty chunks: `0`
- HTML leak chunks: `0`
- Short chunks (`< 50 chars`): `2,726` [cite: 2026-04-27]

## 5. Architecture: The Wisdom Stream Flow
```text
[ Teacher Tablet ]      [ Student Display ]
       ↓                        ↑
[ www.namonexus.com ] ← (WebSocket wss://)
       ↓
[ Cloudflare Tunnel ]
       ↓
[ Lenovo Local Server :8000 ]
  ├── Redis (State/PubSub)
  ├── PostgreSQL (Persistent)
  └── FAISS (Tripitaka Index)
```

## 6. Development Status (Snapshot: 2026-04-28)

| Phase | Description | Status |
| --- | --- | --- |
| P2 | Deep Async Refactor (Backend) | ✅ Complete [cite: 2026-04-27] |
| P3 | Persistent Layer (Redis/PostgreSQL) | ⚠️ Transitional (PostgreSQL/Cloud path wired) [cite: 2026-04-27] |
| P11 | Knowledge Expansion (GCS Re-org) | ✅ Complete (Bucket SMART Pillars implemented) [cite: 2026-04-28] |
| P11V | Batch Vectorizer Automation | ✅ Implemented (Auto-pilot FAISS generation) [cite: 2026-04-28] |
| P15 | GitHub Logic Synchronization | ✅ Complete (Branch `namo` synced with clean .gitignore) [cite: 2026-04-28] |

## 7. Architectural Rules (กฎเหล็ก v5.0.0)
- Port Standard: `8000` (Backend) และ `5173` (Frontend Local)
- Async Integrity: ห้ามใช้ blocking sync I/O ใน endpoint ใหม่เด็ดขาด [cite: 2026-04-22]
- Secret Security: ห้าม hardcode connection string ให้ดึงผ่าน Secret Manager เท่านั้น [cite: 2026-04-22]
- RAG Quality Gate: ก่อน embed ข้อมูล Tripitaka รอบใหม่ ต้องผ่าน Hard/Soft filter เสมอ [cite: 2026-04-27]

## 8. Current Priorities & Next Actions
- **Sentinel Deployment**: ตั้งค่า GitKraken Agent ด้วย Setup Commands (pip installชุดสมบูรณ์) [cite: 2026-04-28]
- **Batch Processing**: เริ่มรัน `batch_vectorizer.py` เพื่อสร้าง Index จากฐานข้อมูล `global_library` [cite: 2026-04-28]
- **Cloud Verification**: ยืนยันการทำงานของระบบ RAG ผ่าน Assets บน GCS [cite: 2026-04-28]
