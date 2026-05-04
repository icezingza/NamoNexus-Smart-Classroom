# ☸️ NamoNexus Resonance Engine (NRE) v5.0.0 — Sovereign Edition

## 1. Project Mental Model
"Infrastructure แห่งปัญญา" ที่เปลี่ยนพระไตรปิฎกให้กลายเป็นระบบห้องเรียนธรรมะอัจฉริยะ (Smart Dhamma Classroom) ผ่านสถาปัตยกรรม Hybrid (Local Edge + Public Cloud)

- Corpus ปัจจุบัน: **168,861 vectors** (dim 384) — ตัวเลข `162,895` ให้ถือเป็น legacy reference เท่านั้น [cite: 2026-04-27]
- Dual-source RAG: **Tripitaka** (primary, 168,861 chunks) + **Global Library** (secondary, 23 FAISS book indexes) [cite: 2026-05-04]
- Both RAG singletons pre-warmed at startup → first teacher query **< 200ms** [cite: 2026-05-04]

## 2. Roles & Identity
- นะโม (Namo): AI Thinking Partner (Gen Z Professional, Blunt, No Fluff) [cite: 2026-02-03]
- พี่ไอซ์ (P'Ice): Tech Monk & AI Architect (Project Owner)
- Claude Code: Senior AI Software Engineer (Backend/Frontend/DevOps)

## 3. Tech Stack: Cloud-Native & Deep Async

### Backend (Lenovo Workstation / Edge Server)
- FastAPI (Async 100%): `asyncio.to_thread` + `aiofiles` throughout [cite: 2026-04-22]
- **Dual-source RAG**: `KnowledgeService.search()` queries Tripitaka retriever (primary) then GlobalLibraryRetriever (secondary, 23 books) — both singletons pre-warmed via `asyncio.gather` in startup event [cite: 2026-05-04]
- FAISS index: `knowledge/tripitaka_main/tripitaka_index.faiss` (168,861 vectors); batch indexes: `knowledge/tripitaka_main/batch_indexes/` (23 books) [cite: 2026-04-28]
- Persistent Layer: SQLite default + Redis PubSub + PostgreSQL/Cloud SQL path for cloud rollout [cite: 2026-04-27]

### Frontend (`namonexus.com`)
- React 18 + Vite: Dual-Screen routing (`/teacher` and `/display`) [cite: 2026-04-27]
- Frontend resolves backend host from `window.location.hostname` at runtime (`vite.config.ts` with `host: true`) [cite: 2026-04-27]
- Real-time: WebSockets + Redis Pub/Sub — latency **< 50ms** confirmed [cite: 2026-05-04]

### Cloud Infrastructure (GCP) — SMART Pillar Storage
- **`namo-classroom-models`**: FAISS indexes + AI models [cite: 2026-04-28]
- **`namonexus-wisdom-storage`**: Tripitaka chunks (168,861 records) [cite: 2026-04-28]
- **`namo-classroom`**: media, logos, frontend assets [cite: 2026-04-28]
- Secrets: `backend/namo_core/config/gcp_secrets.py` → GCP Secret Manager [cite: 2026-04-28]

## 4. One-Click Startup (Local LAN Demo)

```
scripts\Run_NamoNexus.bat          ← Double-click from project root
```

Startup order (auto-polled, no fixed delays):
1. Redis — WSL2 Ubuntu (`wsl -d Ubuntu -u root -- service redis-server start`)
2. Backend — FastAPI on `:8000` (polls `/health` up to 30s)
3. Frontend — Vite dev server on `:5173` (polls TCP up to 20s)
4. Browser — opens `http://localhost:5173/teacher`

**Install desktop shortcut (one-time):**
```
powershell -ExecutionPolicy Bypass -File scripts\Install-Desktop-Shortcut.ps1
```

**Admin credentials (local dev):**
- Username: `admin`
- Password: `1122334455`
- Set in: `backend/namo_core/.env` (`NAMO_ADMIN_USERNAME` / `NAMO_ADMIN_PASSWORD`)
- Login endpoint: `POST /auth/login` → returns JWT Bearer token

## 5. Architecture: The Wisdom Stream Flow
```text
[ Teacher Tablet ]      [ Student Display ]
       ↓                        ↑
[ www.namonexus.com ] ← (WebSocket wss://)
       ↓
[ Cloudflare Tunnel ]
       ↓
[ Lenovo Local Server :8000 ]
  ├── Redis (State/PubSub — classroom_state channel)
  ├── SQLite / PostgreSQL (Persistent)
  └── FAISS — Tripitaka (168,861) + Global Library (23 books)
```

## 6. Knowledge Quality & Automation
- Audit script: `scripts/audit_knowledge_vectors.py`
- **Batch Vectorizer**: `scripts/batch_vectorizer.py` (Auto-pilot JSON Books → FAISS Index) [cite: 2026-04-28]
- Quality filter: `scripts/tripitaka_quality_filter.py` (Hard/Soft filter pre-processing)
- Ingestion: `scripts/master_ingestion.py` (supports `--dry-run`)

### Latest Audit Snapshot (`2026-04-27`)
- Total chunk records: `168,861`
- Average chunk length: `619.25` characters
- Empty chunks: `0` | HTML leak chunks: `0`
- Short chunks (< 50 chars): `2,726`

## 7. Namo-LoRA (Planned)
- **Location**: `tools/lora/` _(directory not yet created)_
- **Purpose**: Fine-tune a domain-adapted model on Tripitaka corpus for higher-quality Dhamma reasoning
- **Status**: Architecture planned — pending batch vectorization completion and GPU resource allocation
- **Prerequisite**: `batch_vectorizer.py` must complete all 23 book indexes before LoRA training data preparation

## 8. Development Status (Snapshot: 2026-05-04)

| Phase | Description | Status |
| --- | --- | --- |
| P2 | Deep Async Refactor (Backend) | ✅ Complete [cite: 2026-04-27] |
| P3 | Persistent Layer (Redis/PostgreSQL) | ⚠️ Transitional (PostgreSQL/Cloud path wired) [cite: 2026-04-27] |
| P11 | Knowledge Expansion (GCS Re-org) | ✅ Complete (Bucket SMART Pillars) [cite: 2026-04-28] |
| P11V | Dual-source RAG + Pre-warm | ✅ Complete — first query < 200ms [cite: 2026-05-04] |
| P12 | Notebook Dashboard (AI Study Tools) | ✅ Complete — 5 modes including audio script [cite: 2026-05-04] |
| P15 | One-Click Desktop Launcher | ✅ Complete — Run_NamoNexus.bat + shortcut installer [cite: 2026-05-04] |
| P16 | Namo-LoRA Fine-tuning | 🔲 Planned (tools/lora/) |

## 9. Architectural Rules (กฎเหล็ก v5.0.0)
- Port Standard: `8000` (Backend) / `5173` (Frontend Local)
- Async Integrity: ห้ามใช้ blocking sync I/O ใน endpoint ใหม่เด็ดขาด [cite: 2026-04-22]
- Secret Security: ห้าม hardcode secrets — ดึงผ่าน `backend/namo_core/.env` → GCP Secret Manager [cite: 2026-04-22]
- RAG Quality Gate: ต้องผ่าน Hard/Soft filter ก่อน embed ทุกครั้ง [cite: 2026-04-27]
- Search Route: ทุก endpoint ที่ค้นหาความรู้ต้องใช้ `KnowledgeService.search()` — ห้ามเรียก `search_tripitaka()` โดยตรง (bypasses global_library) [cite: 2026-05-04]

## 10. Next Actions
- **Namo-LoRA**: สร้าง `tools/lora/` และเริ่ม fine-tuning pipeline
- **PostgreSQL Migration**: ย้ายจาก SQLite → Cloud SQL สำหรับ production
- **Cloud Verification**: ยืนยัน RAG pipeline ผ่าน GCS assets ครบถ้วน
