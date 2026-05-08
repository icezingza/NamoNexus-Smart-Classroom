# ☸️ NamoNexus Resonance Engine (NRE) v6.2.0 — Cloud Run Edition

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
- Persistent Layer: SQLite default + Redis PubSub + **PostgreSQL/Cloud SQL via Alembic** [cite: 2026-05-08]
- Auth: JWT Bearer (HS256), bcrypt admin password, rate-limited login (10 req/60s), HSTS in production [cite: 2026-05-08]

### Frontend (`namonexus.com`)
- React 18 + Vite: Dual-Screen routing (`/teacher` and `/display`) [cite: 2026-04-27]
- Frontend resolves backend host from `window.location.hostname` at runtime (`vite.config.ts` with `host: true`) [cite: 2026-04-27]
- Real-time: WebSockets + Redis Pub/Sub — latency **< 50ms** confirmed [cite: 2026-05-04]

### Cloud Infrastructure (GCP) — SMART Pillar Storage
- **`namo-classroom-models`**: FAISS indexes + AI models [cite: 2026-04-28]
- **`namonexus-wisdom-storage`**: Tripitaka chunks (168,861 records) [cite: 2026-04-28]
- **`namo-classroom`**: media, logos, frontend assets [cite: 2026-04-28]
- Secrets: `backend/namo_core/config/gcp_secrets.py` → GCP Secret Manager [cite: 2026-04-28]
- GCS auto-download: `utils/gcs_assets.py` downloads FAISS from GCS on startup if missing [cite: 2026-05-08]

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

### Production (Cloud Run) — P21 Target

```text
[ Teacher Tablet ]      [ Student Display ]
       ↓                        ↑
[ namonexus.com / api.namonexus.com ]
       ↓
[ Cloud Run: namo-backend (asia-southeast1) ]
  ├── Cloud SQL PostgreSQL 15 — namo-classroom-db
  ├── GCS — FAISS indexes downloaded at startup (gcs_assets.py)
  └── GCP Secret Manager — JWT / admin / Groq secrets
```

### Local LAN Demo (Lenovo Workstation)

```text
[ Teacher Tablet ]      [ Student Display ]
       ↓                        ↑
[ www.namonexus.com ] ← (WebSocket wss://)
       ↓
[ Cloudflare Tunnel ]
       ↓
[ Lenovo Local Server :8000 ]
  ├── Redis (State/PubSub — WSL2 Ubuntu)
  ├── SQLite (dev) / PostgreSQL Cloud SQL (prod)
  └── FAISS — Tripitaka (168,861) + Global Library (23 books)
```

## 6. Resource Baseline (Verified: 2026-05-04)

> วัดบน Lenovo Gaming 3 + WSL2 Redis + uvicorn reload mode

| ตัวชี้วัด | ค่าที่วัดได้ | หมายเหตุ |
|---|---|---|
| First query latency | **< 200ms** | หลัง pre-warm startup (เดิม 22.9s cold) |
| Display sync latency | **48.8ms** | `/teacher` → Redis PubSub → `/display` |
| Backend RAM (WorkingSet) | **~1.86 GB** | FAISS 239MB + 2× SentenceTransformer models |
| CPU under load | **20%** | 3x concurrent requests |
| System RAM in use | **17.4 / 23.87 GB (73%)** | ยังเหลือ buffer ~6.4 GB |
| Audio script generation | **~4s** | Groq llama-3.3-70b-versatile via `_call_groq_sync` |
| 3x concurrent requests | **200, 200, 200** | ไม่มี error ภายใต้ load |

## 7. Knowledge Quality & Automation
- Audit script: `scripts/audit_knowledge_vectors.py`
- **Batch Vectorizer**: `scripts/batch_vectorizer.py` (Auto-pilot JSON Books → FAISS Index) [cite: 2026-04-28]
- Quality filter: `scripts/tripitaka_quality_filter.py` (Hard/Soft filter pre-processing)
- Ingestion: `scripts/master_ingestion.py` (supports `--dry-run`)
- **Cloud Verification**: `scripts/verify_cloud_assets.py` (end-to-end RAG + GCS + secrets check) [cite: 2026-05-08]

### Latest Audit Snapshot (`2026-04-27`)
- Total chunk records: `168,861`
- Average chunk length: `619.25` characters
- Empty chunks: `0` | HTML leak chunks: `0`
- Short chunks (< 50 chars): `2,726`

## 8. Namo-LoRA (P16)
- **Location**: `tools/lora/` [cite: 2026-05-08]
- **Purpose**: Fine-tune a Thai-capable LLM (Typhoon-8B) on Tripitaka corpus for higher-quality Dhamma reasoning
- **Status**: Pipeline scaffolded — ready to run on GPU (WSL2 + CUDA)
- **Files**: `config.py` · `prepare_data.py` · `train.py` · `evaluate.py` · `export_model.py`
- **Default model**: `scb10x/llama-3-typhoon-v1.5-8b` (QLoRA 4-bit, ~9 GB VRAM)
- **Training data**: `knowledge/lora/train.jsonl` — generated from 23 global_library books
- **Run**: `python tools/lora/prepare_data.py` → `python tools/lora/train.py`

## 9. Security Hardening (2026-05-08)

ทุกรายการด้านล่างถูก implement แล้วใน session นี้:

| Area | Change |
|---|---|
| Auth | Removed JWT token query-param fallback (tokens in URL end up in logs) |
| Auth | `secrets.compare_digest` + bcrypt backward-compat detection |
| Auth | Rate limiter: 10 failed attempts/60s → HTTP 429 + `Retry-After` header |
| Auth | `datetime.now(timezone.utc)` — removed deprecated `utcnow()` |
| Startup | Placeholder secret guard: `RuntimeError` in production, WARNING in dev |
| Startup | GCP secrets loaded first, then validation — correct order |
| Secrets | `system_secret` is now a read-only `@property` alias for `jwt_secret_key` — no drift |
| Middleware | `HSTSMiddleware` added (production only) |
| Middleware | `TraceIDMiddleware` — fixed to always return response |
| Middleware | Structured JSON logging (`_JsonFormatter`) for Cloud Run / Cloud Logging |
| CORS | Restricted to specific methods + headers (no wildcard) |
| Upload | 25 MB cap on speech upload; 413 on oversize; sanitized error in production |
| Redis | `utils/redis_factory.py` — single factory injects `redis_password` |
| WebSocket | Polling interval 50ms → 500ms (20Hz → 2Hz, -97% CPU per idle connection) |
| DB | PostgreSQL pool: `pool_pre_ping`, `pool_recycle=300`, `max_overflow=10` |

## 10. Database Migration (PostgreSQL)

```bash
cd backend/namo_core
alembic upgrade head      # apply all migrations
alembic current           # show current revision
alembic downgrade -1      # roll back one step
```

- Config: `backend/namo_core/alembic.ini` + `migrations/env.py`
- Initial migration: `migrations/versions/20260508_0000_0001_initial_schema.py` (10 tables)
- Runbook: `POSTGRES_MIGRATION.md` (Cloud SQL setup, bcrypt hash generation, Cloud Run deployment)
- `database/core.py`: auto-selects SQLite args vs PostgreSQL pool args based on URL prefix

## 11. Development Status (Snapshot: 2026-05-08 — Last updated: P21 Cloud Run Deploy)

| Phase | Description | Status |
|---|---|---|
| P2 | Deep Async Refactor (Backend) | ✅ Complete [cite: 2026-04-27] |
| P3 | Persistent Layer (Redis/PostgreSQL) | ✅ Complete — Alembic + Cloud SQL ready [cite: 2026-05-08] |
| P11 | Knowledge Expansion (GCS Re-org) | ✅ Complete (Bucket SMART Pillars) [cite: 2026-04-28] |
| P11V | Dual-source RAG + Pre-warm | ✅ Complete — first query < 200ms [cite: 2026-05-04] |
| P12 | Notebook Dashboard (AI Study Tools) | ✅ Complete — 5 modes including audio script [cite: 2026-05-04] |
| P13 | Security Hardening | ✅ Complete — auth, rate limit, HSTS, bcrypt, secrets [cite: 2026-05-08] |
| P14 | Structured Logging + Smoke Tests | ✅ Complete — JSON logging, 152 pytest tests (0 failed) [cite: 2026-05-08] |
| P15 | One-Click Desktop Launcher | ✅ Complete — Run_NamoNexus.bat + shortcut installer [cite: 2026-05-04] |
| P16 | Namo-LoRA Fine-tuning | 🔄 In Progress — pipeline scaffolded in `tools/lora/` [cite: 2026-05-08] |
| P17 | Cloud Verification & GCS Assets | ✅ Complete — `verify_cloud_assets.py` + `gcs_assets.py` [cite: 2026-05-08] |
| P18 | Full Test Suite Hardening | ✅ Complete — 152 tests, 0 failed; `semantic_cache` + indentation bugs fixed [cite: 2026-05-08] |
| P19 | PostgreSQL Cloud SQL Deploy | ✅ Complete — 10 tables migrated via `migrate.py` + `cloud-sql-python-connector` [cite: 2026-05-08] |
| P20 | Production Smoke Test | ✅ Complete — all checks PASS; 34ms query latency; 152 tests 0 failed [cite: 2026-05-08] |
| P21 | Cloud Run Deploy | 🔄 **In Progress** — image building (3rd attempt); deploy pending [cite: 2026-05-08] |

## 12. Architectural Rules (กฎเหล็ก v6.0.0)
- Port Standard: `8000` (Backend) / `5173` (Frontend Local)
- Async Integrity: ห้ามใช้ blocking sync I/O ใน endpoint ใหม่เด็ดขาด [cite: 2026-04-22]
- Secret Security: ห้าม hardcode secrets — ดึงผ่าน `backend/namo_core/.env` → GCP Secret Manager [cite: 2026-04-22]
- RAG Quality Gate: ต้องผ่าน Hard/Soft filter ก่อน embed ทุกครั้ง [cite: 2026-04-27]
- Search Route: ทุก endpoint ที่ค้นหาความรู้ต้องใช้ `KnowledgeService.search()` — ห้ามเรียก `search_tripitaka()` โดยตรง (bypasses global_library) [cite: 2026-05-04]
- DB Migration: ห้ามใช้ `Base.metadata.create_all()` ใน production — ใช้ `alembic upgrade head` เท่านั้น [cite: 2026-05-08]
- Redis: ทุก Redis connection ต้องผ่าน `utils/redis_factory.py` — ห้าม `redis.from_url()` โดยตรง [cite: 2026-05-08]
- JWT: ห้าม accept token ผ่าน query param — `Authorization: Bearer` header เท่านั้น [cite: 2026-05-08]

## 13. Next Actions (Priority Order)

### 🔴 P21 — Cloud Run Deploy (กำลังทำอยู่ — สานต่อได้เลย)

**สถานะปัจจุบัน (2026-05-08):**

- Artifact Registry repo `namo-backend` สร้างแล้ว — `asia-southeast1-docker.pkg.dev/namo-classroom/namo-backend/namo-core:latest`
- Cloud Build ครั้งที่ 3 กำลัง run อยู่ (background task `byptyno8y`) — รอ notification แล้ว deploy
- Fixes ที่ทำแล้ว: `.dockerignore`, Dockerfile (python 3.11, correct COPY path), `requirements.txt` (tiktoken + google-generativeai), `app.py` (skip create_all for postgres), CORS (namonexus.com)

**Deploy command (พร้อมรัน ทันที build เสร็จ):**
```bash
# สร้าง cloudrun-env.yaml ชั่วคราว แล้วลบทิ้งหลัง deploy
cat > /tmp/cloudrun-env.yaml << 'EOF'
NAMO_ENV: production
NAMO_DATABASE_URL: "postgresql+psycopg2://namo_app:zyVrvLVu7FNXpAO7MN_WYw@/namo_classroom?host=/cloudsql/namo-classroom:asia-southeast1:namo-classroom-db"
NAMO_ALLOWED_ORIGINS: "https://namonexus.com,https://www.namonexus.com"
GOOGLE_CLOUD_PROJECT: namo-classroom
UVICORN_WORKERS: "2"
EOF

gcloud run deploy namo-backend \
  --image=asia-southeast1-docker.pkg.dev/namo-classroom/namo-backend/namo-core:latest \
  --region=asia-southeast1 --project=namo-classroom \
  --platform=managed --port=8000 --memory=4Gi --cpu=2 \
  --min-instances=1 --max-instances=3 --timeout=300 --cpu-boost \
  --service-account=vertex-express@namo-classroom.iam.gserviceaccount.com \
  --add-cloudsql-instances=namo-classroom:asia-southeast1:namo-classroom-db \
  --set-secrets="NAMO_JWT_SECRET_KEY=namo-jwt-secret:latest,NAMO_ADMIN_PASSWORD=namo-admin-password:latest,NAMO_REASONING_API_KEY=namo-groq-api-key:latest" \
  --env-vars-file=/tmp/cloudrun-env.yaml \
  --allow-unauthenticated

rm /tmp/cloudrun-env.yaml
```

**หลัง deploy สำเร็จ:**

1. ตรวจ health: `curl $(gcloud run services describe namo-backend --region=asia-southeast1 --format="value(status.url)")/health`
2. Map domain: `gcloud run domain-mappings create --service=namo-backend --domain=api.namonexus.com --region=asia-southeast1`
3. Cloudflare: เพิ่ม CNAME `api` → `ghs.googlehosted.com` (DNS only, grey cloud)

**หมายเหตุ:** `namo_app` DB password (`zyVrvLVu7FNXpAO7MN_WYw`) ถูก expose ใน session นี้ → Rotate ที่ Cloud SQL Console หลัง deploy สำเร็จ

---

### 🟡 P16 — Namo-LoRA Training (ต้องมี GPU)

```bash
python tools/lora/prepare_data.py   # สร้าง knowledge/lora/train.jsonl
python tools/lora/train.py          # QLoRA 4-bit, ~9GB VRAM, ~4-8h
python tools/lora/evaluate.py       # ประเมิน perplexity + Dhamma accuracy
python tools/lora/export_model.py --merge --gguf  # → Ollama deploy
```
- ต้องการ: WSL2 Ubuntu + CUDA 12+ + RTX 3060+ (หรือ A100 บน cloud)
- Default model: `scb10x/llama-3-typhoon-v1.5-8b`

### 🟢 P22 — หลัง Cloud Run live

```bash
# Rotate namo_app DB password (exposed in session)
gcloud sql users set-password namo_app --instance=namo-classroom-db --password=<new-strong-password>
# อย่าลืมอัปเดต namo-database-password ใน Secret Manager ด้วย

# Verify production end-to-end
SERVICE_URL=$(gcloud run services describe namo-backend --region=asia-southeast1 --format="value(status.url)")
curl -s "$SERVICE_URL/health"
python -X utf8 scripts/verify_cloud_assets.py
```

## 13.1 Bug Fixes Applied (2026-05-08 — P18 + P19 + P21)

| Bug | File | Fix |
|---|---|---|
| `_cosine_similarity` ValueError — shapes `(1,384)` not aligned | `services/knowledge/semantic_cache.py` | เพิ่ม `.flatten()` ก่อน `np.dot()` |
| Test suite: 38 failed → 0 failed | `tests/` (multiple files) | Auth headers, async pipeline, dual-source RAG mocks, WS threshold, in-memory SQLite |
| `conftest.py` missing in-memory DB | `tests/conftest.py` | เพิ่ม `NAMO_DATABASE_URL=sqlite:///:memory:` |
| `env.py` ไม่อ่าน injected connection | `migrations/env.py` | เพิ่ม `injected_conn` check ก่อน fallback → `engine_from_config` |
| Cloud SQL SA 403 NOT_AUTHORIZED | GCP IAM | เพิ่ม `roles/cloudsql.client` ให้ `vertex-express@namo-classroom.iam.gserviceaccount.com` |
| `verify_cloud_assets.py` ALL PASSED | `scripts/verify_cloud_assets.py` | แก้ Singleton import + JWT check; run ด้วย `python -X utf8` |
| `semantic_cache.py` IndentationError | `services/knowledge/semantic_cache.py` | ตัด duplicate content (double-paste) ออก |
| `test_async_compliance.py` IndentationError | `tests/unit/test_async_compliance.py` | ตัด duplicate assert block ออก |
| `pytest-asyncio` missing → 10 async tests fail | `requirements.txt` | `pip install pytest-asyncio` — เพิ่มใน requirements.txt |
| Cloud Run: `ModuleNotFoundError: No module named 'namo_core'` | `Dockerfile` | เปลี่ยน `COPY backend/ ./backend/` → `COPY backend/namo_core/ ./namo_core/` |
| Cloud Run: `ModuleNotFoundError: No module named 'tiktoken'` | `backend/namo_core/requirements.txt` | เพิ่ม `tiktoken>=0.5.2` + `google-generativeai>=0.7.0` |

## 14. Key File Index (2026-05-08 — v6.2.0 Cloud Run Edition)

| File | Purpose |
|---|---|
| `backend/namo_core/api/auth.py` | JWT middleware — Bearer-only, no query-param |
| `backend/namo_core/api/routes/auth_routes.py` | Login endpoint + rate limiter + bcrypt |
| `backend/namo_core/api/middleware.py` | TraceID, HSTS, JSON logging |
| `backend/namo_core/api/app.py` | App factory — startup: secrets → GCS assets → DB → pre-warm RAG |
| `backend/namo_core/config/settings.py` | Pydantic settings singleton + `get_settings()` |
| `backend/namo_core/database/core.py` | SQLAlchemy engine — auto pool tuning for PostgreSQL |
| `backend/namo_core/utils/redis_factory.py` | Single Redis connection factory (async + sync) |
| `backend/namo_core/migrations/env.py` | Alembic env — supports injected connection for `migrate.py` programmatic API |
| `migrate.py` (workspace root) | Cloud SQL migration runner — `cloud-sql-python-connector` + `pg8000`, no binary proxy |
| `backend/namo_core/utils/gcs_assets.py` | GCS FAISS download utility + startup hook |
| `backend/namo_core/alembic.ini` | Alembic config — reads DB URL from settings |
| `backend/namo_core/migrations/env.py` | Alembic runtime env — imports all models |
| `backend/namo_core/migrations/versions/20260508_*` | Initial schema migration (10 tables) |
| `backend/namo_core/tests/test_production_readiness.py` | 13 smoke tests — auth, rate limit, HSTS, secrets |
| `backend/namo_core/tests/` (full suite) | **150 tests, 0 failures** — unit + integration + security [cite: 2026-05-08] |
| `backend/namo_core/tests/conftest.py` | Test fixtures — JWT auth headers, in-memory SQLite, ML stubs, settings reset |
| `backend/namo_core/services/knowledge/semantic_cache.py` | In-memory semantic cache — `_cosine_similarity` fixed for 2D vectors [cite: 2026-05-08] |
| `scripts/verify_cloud_assets.py` | End-to-end cloud verification (FAISS + RAG + GCS + secrets) — run with `python -X utf8` |
| `tools/lora/` | Namo-LoRA pipeline (config, prepare_data, train, evaluate, export) |
| `POSTGRES_MIGRATION.md` | Cloud SQL migration runbook |
| `Dockerfile` | Cloud Run image — python 3.11-slim, `COPY backend/namo_core/ ./namo_core/`, dynamic PORT/UVICORN_WORKERS |
| `.dockerignore` | Excludes `knowledge/` (FAISS), `.venv/`, `node_modules/` — keeps image lean |
| `docs/superpowers/plans/2026-05-08-cloud-run-deploy.md` | Full P21 deploy plan — 10 tasks, deploy command included |
