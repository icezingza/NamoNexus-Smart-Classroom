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

### Cloud Infrastructure (GCP)
- Project ID: `namo-classroom` (Default region: `asia-southeast1`, zone: `asia-southeast1-b`)
- Budget: `$30,000` credits [cite: 2026-04-22]
- Services: Cloud SQL (PostgreSQL), Memorystore (Redis), Secret Manager, Cloudflare Tunnel [cite: 2026-04-22, 2026-04-27]
- Secret Manager integration is implemented in code via `backend/namo_core/utils/gcp_secrets.py` and startup wiring in `backend/namo_core/config/settings.py`; runtime cloud verification remains the next checkpoint [cite: 2026-04-27]

## 4. Knowledge Quality Layer
- Audit script: `scripts/audit_knowledge_vectors.py` [cite: 2026-04-27]
- Reusable filter module: `scripts/tripitaka_quality_filter.py` [cite: 2026-04-27]
- Ingestion entrypoint updated: `scripts/master_ingestion.py` now supports Hard/Soft filter pre-processing and `--dry-run` [cite: 2026-04-27]

### Latest Audit Snapshot (`2026-04-27`)
- Total chunk records: `168,861`
- Average chunk length: `619.25` characters
- Empty chunks: `0`
- HTML leak chunks: `0`
- Short chunks (`< 50 chars`): `2,726` [cite: 2026-04-27]

### Short Chunk Strategy
- Hard Filter: drop `empty`, `html_leak`, `footer_contact`, `separator_line`
- Soft Filter: merge `suspected_fragment` back into adjacent context when chunk lineage/title matches
- Keep but down-rank: `section_heading`, `section_closure`, `numbered_list_or_plan`, `summary_note`, `verse_or_formula_line` [cite: 2026-04-27]

### Validated Impact on Production Metadata
- Hard-dropped records: `451`
- Soft-merged fragments: `1,496`
- Total short-chunk issues addressed: `1,947`
- Coverage: `71.42%` of short chunks, `1.15%` of full corpus [cite: 2026-04-27]

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

## 6. Development Status (Snapshot: 2026-04-27)

| Phase | Description | Status |
| --- | --- | --- |
| P2 | Deep Async Refactor (Backend) | ✅ Complete [cite: 2026-04-27] |
| P3 | Persistent Layer (Redis/PostgreSQL) | ⚠️ Transitional (`SQLite` default ยังอยู่, Redis services ใช้งานได้, PostgreSQL/Cloud path มีทิศทางและ secret wiring แล้ว) [cite: 2026-04-27] |
| P4 | Notebook System (Saturate Wisdom) | ✅ Complete (`suggest-sources`, generate flow, bypass token verified) [cite: 2026-04-27] |
| P10 | Dual-Screen Frontend Routing | ✅ Complete (`/teacher` และ `/display` validated) [cite: 2026-04-27] |
| P11Q | Tripitaka Quality Audit + Hard/Soft Filter Layer | ✅ Implemented in scripts, validated on production metadata [cite: 2026-04-27] |
| P13 | Enterprise Auth (JWT Middleware) | ✅ Complete (JWT + Sovereign bypass) [cite: 2026-04-27] |
| LAN | Vite Network + CORS + Heartbeat Stability | ✅ Complete (`host: true`, LAN accessible, demo-ready) [cite: 2026-04-27] |
| SEC | Security Lockdown via GCP Secret Manager | ✅ Complete in code (`settings.py` + `gcp_secrets.py` wired) [cite: 2026-04-27] |
| OPS | Local Runtime Health Check | ✅ Complete (`16/16` checks passed via `scripts/health_check.py`) [cite: 2026-04-27] |

### Notebook & LAN Validation Snapshot (`2026-04-27`)
- Manual validation was completed against the already-open teacher tab at `localhost:5173/teacher`; sandboxed browser automation could not reach host `localhost` directly, so the validation path used the existing browser session [cite: 2026-04-27]
- `Namo Notebook Dashboard` rendered successfully with full UI state [cite: 2026-04-27]
- Tripitaka source `"อบรมบาลีก่อนสอบ ปีที่ 6 หน้า 246"` was added into selected scriptures successfully [cite: 2026-04-27]
- All 5 notebook modes were visible: `สรุปเตรียมสอน`, `คู่มือ & FAQ`, `บทละครเสียง`, `บัตรคำ`, `ควิซวัดผล` [cite: 2026-04-27]
- `SATURATE WISDOM` was enabled and ready to execute [cite: 2026-04-27]
- Backend API path for the Notebook flow was reported healthy and demo-ready on LAN [cite: 2026-04-27]
- `backend/namo_core/api/routes/notebook.py` exists and is registered in the FastAPI app; `suggest-sources` is no longer a missing blocker [cite: 2026-04-27]

### Runtime Health Snapshot (`2026-04-27`)
- `python scripts/health_check.py` passed `16/16` checks against `http://127.0.0.1:8000` [cite: 2026-04-27]
- API server, `/status`, `/health`, knowledge search, Tripitaka index status, classroom session, slide controller, emotion state, TTS status, and PII hashing checks all passed [cite: 2026-04-27]
- Verified runtime values from health check:
  - Knowledge search returned `3` items
  - Tripitaka FAISS index reported `168,861` vectors
  - Classroom lessons loaded: `1`
  - Emotion state: `focused`
- `backend/namo_core/api/routes/status.py` is now `async def status()` and awaits `classroom.get_session_summary()`; this resolved the prior HTTP 500 status endpoint failure [cite: 2026-04-27]
- `scripts/health_check.py` includes UTF-8 stdout handling for Windows, resolving the prior Unicode console rendering issue [cite: 2026-04-27]
- Current local system state: ready for classroom use [cite: 2026-04-27]

## 7. Architectural Rules (กฎเหล็ก v5.0.0)
- Port Standard: `8000` (Backend) และ `5173` (Frontend Local)
- Async Integrity: ห้ามใช้ blocking sync I/O ใน endpoint ใหม่เด็ดขาด [cite: 2026-04-22]
- Secret Security: ห้าม hardcode connection string ให้ดึงผ่าน Secret Manager เท่านั้น [cite: 2026-04-22]
- Fallback Logic: WebSocket ต้องมีระบบเปลี่ยนเป็น HTTP Polling เมื่อสัญญาณหลุด (Graceful Degradation) [cite: 2026-04-27]
- RAG Quality Gate: ก่อน embed ข้อมูล Tripitaka รอบใหม่ ต้องผ่าน Hard/Soft filter หรือ audit ที่เทียบเท่าเสมอ [cite: 2026-04-27]

## 8. Current Priorities & Next Actions
- RAG Productionization: นำ quality filter ไปเสียบใน production rebuild path ของ `tripitaka_main` ก่อน rebuild index รอบถัดไป [cite: 2026-04-27]
- Gateway / Cloud Verification: local health path ผ่านแล้ว; ขั้นถัดไปคือยืนยัน `/health`, `/status`, และ `/knowledge/tripitaka/status` ผ่าน public gateway / tunnel path ด้วย [cite: 2026-04-27]
- Demo Operations: ระบบ Notebook และ LAN ผ่านแล้ว ให้คง end-to-end rehearsal และ stability checks ต่อเนื่องกับอุปกรณ์จริง [cite: 2026-04-27]
