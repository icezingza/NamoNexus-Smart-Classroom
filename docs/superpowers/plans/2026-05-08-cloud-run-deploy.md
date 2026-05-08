# Cloud Run Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy NamoNexus backend to Google Cloud Run (asia-southeast1) so `api.namonexus.com` routes to a live production service with PostgreSQL + GCS FAISS + Secret Manager wired.

**Architecture:** Docker image built from `backend/namo_core/` pushed to Artifact Registry → Cloud Run pulls image, mounts Cloud SQL Unix socket, downloads FAISS from GCS at startup, reads all secrets from GCP Secret Manager. Redis handled by Upstash (serverless, no VPC required).

**Tech Stack:** Python 3.11-slim, FastAPI/uvicorn, Cloud Run (asia-southeast1), Artifact Registry, Cloud SQL (PostgreSQL 15), GCS (FAISS indexes), GCP Secret Manager, Upstash Redis.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `Dockerfile` | **Modify** | Fix module path, prod deps, correct COPY context |
| `.dockerignore` | **Create** | Exclude FAISS/venv/node_modules — keep image lean |
| `backend/namo_core/requirements.txt` | **Modify** | Add bcrypt, slowapi, aiofiles; remove sounddevice |
| `backend/namo_core/api/app.py` | **Modify** | Skip `create_all` for PostgreSQL; fix deprecated startup event |
| `backend/namo_core/config/settings.py` | **Modify** | Add `namonexus.com` to default allowed origins |

---

## Task 1: Create `.dockerignore`

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1: Create `.dockerignore` to exclude heavy paths from build context**

```
# FAISS indexes (downloaded from GCS at runtime — do NOT bake into image)
knowledge/

# Python virtual environments
.venv/
venv/
backend/namo_core/venv/

# Node.js
node_modules/
frontend/node_modules/

# Compiled Python
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg-info/
dist/
build/

# Local databases
*.db
*.sqlite3

# Logs and temp
logs/
*.log
tmp/
.tmp/

# Test artifacts
.pytest_cache/
.coverage
htmlcov/

# Git
.git/
.gitignore

# Docs and scripts not needed at runtime
docs/
scripts/
tools/
NamoNexus-Skills/
NamoNexus-Smart-Classroom.worktrees/

# Secrets — never bake into image
*.pem
*.key
.gcp/
```

- [ ] **Step 2: Verify build context size drops**

```bash
# From project root — count files that WOULD be sent to Docker
find . -not -path './.git/*' | wc -l
# With .dockerignore in place, run:
docker build --no-cache --dry-run . 2>&1 | head -5
# Expected: context size < 50 MB (vs ~2 GB without .dockerignore)
```

- [ ] **Step 3: Commit**

```bash
git add .dockerignore
git commit -m "build: add .dockerignore — exclude FAISS/venv/knowledge from image context"
```

---

## Task 2: Fix Dockerfile

**Files:**
- Modify: `Dockerfile`

Current problems:
- CMD references `backend.namo_core.main:app` — wrong, should be `namo_core.api.app:app`
- Copies root `requirements.txt` (stale) — should copy `backend/namo_core/requirements.txt`
- No `--workers` for production throughput
- Python 3.10 (EOL 2026-10) — upgrade to 3.11-slim
- Missing build deps for `psycopg2-binary` and `sentence-transformers`

- [ ] **Step 1: Replace Dockerfile with production-correct version**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps: gcc for psycopg2-binary build; curl for healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cached unless requirements change)
COPY backend/namo_core/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source only (knowledge/ excluded via .dockerignore)
COPY backend/ ./backend/

# Cloud Run injects PORT env var; default 8000 matches our settings
EXPOSE 8000

# 2 workers: Cloud Run 2-CPU allocation; adjust via UVICORN_WORKERS env var
CMD ["sh", "-c", "uvicorn namo_core.api.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${UVICORN_WORKERS:-2}"]
```

- [ ] **Step 2: Verify CMD resolves correctly (dry-run)**

```bash
# From project root
docker build -t namo-backend:local . 2>&1 | tail -10
# Expected: Successfully built <id>
# Expected: No "module not found" errors
```

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "build: fix Dockerfile — correct module path, python 3.11, prod CMD"
```

---

## Task 3: Update `requirements.txt` for Cloud Run

**Files:**
- Modify: `backend/namo_core/requirements.txt`

Problems: `sounddevice` won't install in container (no audio hw); missing `bcrypt`, `slowapi`, `aiofiles`, `cloud-sql-python-connector`.

- [ ] **Step 1: Update `backend/namo_core/requirements.txt`**

```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
httpx>=0.27.0
python-multipart>=0.0.9
numpy
faiss-cpu>=1.7.4
sentence-transformers>=3.0.0
# Speech (optional — used by local server only; gracefully skipped in Cloud Run)
# openai-whisper
# faster-whisper>=1.0.0
# sounddevice
edge-tts>=6.6.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
alembic>=1.13.0
PyJWT>=2.8.0
bcrypt>=4.0.0
slowapi>=0.1.9
aiofiles>=23.0.0
cloud-sql-python-connector[pg8000]>=1.0.0
google-cloud-secret-manager>=2.20.0
google-cloud-storage>=2.14.0
redis>=5.0.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 2: Verify install locally (catch any conflicts)**

```bash
cd backend/namo_core
pip install -r requirements.txt --dry-run 2>&1 | grep -E "ERROR|CONFLICT|Would install" | head -20
# Expected: no ERROR or CONFLICT lines
```

- [ ] **Step 3: Commit**

```bash
git add backend/namo_core/requirements.txt
git commit -m "deps: add bcrypt/slowapi/aiofiles/cloud-sql-connector; remove audio libs for Cloud Run"
```

---

## Task 4: Fix `app.py` — Skip `create_all` for PostgreSQL

**Files:**
- Modify: `backend/namo_core/api/app.py:110-116`

`Base.metadata.create_all()` in production bypasses Alembic migrations. Must skip for PostgreSQL (migration already applied via `migrate.py`).

- [ ] **Step 1: Replace the `create_all` block (lines 110-115) in `app.py`**

Find:
```python
        # Phase 12: auto-create all tables (idempotent — safe to run on every start)
        try:
            Base.metadata.create_all(bind=engine)
            _logger.info("[DB] SQLite tables created/verified OK")
        except Exception as exc:
            _logger.error("[DB] Failed to create tables: %s", exc)
```

Replace with:
```python
        # SQLite only: auto-create tables for local dev.
        # PostgreSQL uses Alembic migrations (alembic upgrade head) — never create_all.
        _db_url: str = settings.database_url or ""
        if not _db_url.startswith("postgresql"):
            try:
                Base.metadata.create_all(bind=engine)
                _logger.info("[DB] SQLite tables created/verified OK")
            except Exception as exc:
                _logger.error("[DB] Failed to create tables: %s", exc)
        else:
            _logger.info("[DB] PostgreSQL detected — skipping create_all (use alembic upgrade head)")
```

- [ ] **Step 2: Run pytest to confirm no regressions**

```bash
cd backend
python -m pytest namo_core/tests/ -q --tb=short 2>&1 | tail -5
# Expected: 152 passed, 0 failed
```

- [ ] **Step 3: Commit**

```bash
git add backend/namo_core/api/app.py
git commit -m "fix: skip Base.metadata.create_all for PostgreSQL — use Alembic only"
```

---

## Task 5: Add Production CORS Origins

**Files:**
- Modify: `backend/namo_core/config/settings.py:18`

- [ ] **Step 1: Update default `allowed_origins` to include production domains**

Find in `settings.py`:
```python
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
```

Replace with:
```python
    allowed_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "https://namonexus.com,"
        "https://www.namonexus.com"
    )
```

- [ ] **Step 2: Verify origin list parses correctly**

```bash
cd backend/namo_core
python -c "
from namo_core.config.settings import get_settings
s = get_settings()
print(s.origin_list)
"
# Expected: ['http://localhost:5173', 'http://127.0.0.1:5173', 'https://namonexus.com', 'https://www.namonexus.com']
```

- [ ] **Step 3: Commit**

```bash
git add backend/namo_core/config/settings.py
git commit -m "config: add namonexus.com to default CORS allowed origins"
```

---

## Task 6: Create Artifact Registry Repo + Configure Docker Auth

**Files:** none (GCP infra)

- [ ] **Step 1: Create Artifact Registry repository**

```bash
gcloud artifacts repositories create namo-backend \
  --repository-format=docker \
  --location=asia-southeast1 \
  --description="NamoNexus backend Docker images" \
  --project=namo-classroom
# Expected: Created repository [namo-backend]
```

- [ ] **Step 2: Configure Docker to authenticate with Artifact Registry**

```bash
gcloud auth configure-docker asia-southeast1-docker.pkg.dev --quiet
# Expected: Docker credential helper updated for asia-southeast1-docker.pkg.dev
```

- [ ] **Step 3: Tag image for Artifact Registry**

```bash
# IMAGE_TAG format: asia-southeast1-docker.pkg.dev/<PROJECT>/<REPO>/<IMAGE>:<TAG>
export IMAGE="asia-southeast1-docker.pkg.dev/namo-classroom/namo-backend/namo-core:latest"
echo "Image: $IMAGE"
```

---

## Task 7: Build & Push Docker Image

**Files:** none (Docker build)

- [ ] **Step 1: Build image from project root**

```bash
cd C:\Users\icezi\NamoNexus-Smart-Classroom
IMAGE="asia-southeast1-docker.pkg.dev/namo-classroom/namo-backend/namo-core:latest"
docker build -t $IMAGE . 2>&1 | tee logs/docker-build.log
# Expected: Successfully built ... Successfully tagged ...
# Expected build time: 3-8 min (sentence-transformers is large)
```

- [ ] **Step 2: Verify image size**

```bash
docker images $IMAGE --format "{{.Size}}"
# Expected: < 4 GB (sentence-transformers ~1.5GB, faiss-cpu ~200MB)
# If > 5 GB: check .dockerignore excluded knowledge/ and venv/
```

- [ ] **Step 3: Push to Artifact Registry**

```bash
docker push $IMAGE 2>&1 | tee logs/docker-push.log
# Expected: Pushed ... digest: sha256:...
```

---

## Task 8: Deploy to Cloud Run

**Files:** none (gcloud commands)

Cloud Run configuration:
- `--memory=4Gi` — FAISS (259MB) + 2× SentenceTransformer models (~1.5GB) + overhead
- `--cpu=2` — concurrent requests under load
- `--min-instances=1` — avoid cold start for classroom (pre-warm RAG takes ~11s cold)
- `--add-cloudsql-instances` — Unix socket mount for PostgreSQL
- All secrets via Secret Manager (not env vars)

- [ ] **Step 1: Set shell variables**

```bash
PROJECT="namo-classroom"
REGION="asia-southeast1"
SERVICE="namo-backend"
IMAGE="asia-southeast1-docker.pkg.dev/namo-classroom/namo-backend/namo-core:latest"
SQL_CONN="namo-classroom:asia-southeast1:namo-classroom-db"
```

- [ ] **Step 2: Store Upstash Redis URL in Secret Manager**

> Get free Redis at https://upstash.com → create DB in `ap-southeast-1` → copy `REDIS_URL`

```bash
# Replace <UPSTASH_REDIS_URL> with the actual URL from Upstash dashboard
echo -n "rediss://<user>:<pass>@<host>:6379" | \
  gcloud secrets create namo-redis-url \
    --data-file=- \
    --project=$PROJECT
# Expected: Created version [1] of secret [namo-redis-url]
```

- [ ] **Step 3: Deploy to Cloud Run**

```bash
gcloud run deploy $SERVICE \
  --image=$IMAGE \
  --region=$REGION \
  --project=$PROJECT \
  --platform=managed \
  --port=8000 \
  --memory=4Gi \
  --cpu=2 \
  --min-instances=1 \
  --max-instances=3 \
  --timeout=300 \
  --concurrency=80 \
  --service-account=vertex-express@namo-classroom.iam.gserviceaccount.com \
  --add-cloudsql-instances=$SQL_CONN \
  --set-secrets="NAMO_JWT_SECRET_KEY=namo-jwt-secret:latest,NAMO_ADMIN_PASSWORD=namo-admin-password:latest,NAMO_REASONING_API_KEY=namo-groq-api-key:latest,NAMO_REDIS_URL=namo-redis-url:latest" \
  --set-env-vars="NAMO_ENV=production,NAMO_DATABASE_URL=postgresql+psycopg2://namo_app:zyVrvLVu7FNXpAO7MN_WYw@/namo_classroom?host=/cloudsql/namo-classroom:asia-southeast1:namo-classroom-db,NAMO_ALLOWED_ORIGINS=https://namonexus.com,https://www.namonexus.com,GOOGLE_CLOUD_PROJECT=namo-classroom,UVICORN_WORKERS=2" \
  --allow-unauthenticated
# Expected: Service [namo-backend] revision ... deployed ... URL: https://namo-backend-xxxx-as.a.run.app
```

- [ ] **Step 4: Note the Cloud Run URL**

```bash
gcloud run services describe $SERVICE \
  --region=$REGION \
  --project=$PROJECT \
  --format="value(status.url)"
# Save this URL — needed for Cloudflare DNS routing
```

---

## Task 9: Verify Production Deployment

- [ ] **Step 1: Smoke test health endpoint**

```bash
SERVICE_URL=$(gcloud run services describe namo-backend \
  --region=asia-southeast1 --project=namo-classroom \
  --format="value(status.url)")

curl -s "$SERVICE_URL/health" | python -m json.tool
# Expected: {"status": "ok", ...}
```

- [ ] **Step 2: Test authenticated endpoint**

```bash
# Get JWT token
TOKEN=$(curl -s -X POST "$SERVICE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"1122334455"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: ${TOKEN:0:20}..."

# Test knowledge search
curl -s "$SERVICE_URL/knowledge/search?q=อริยสัจ" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool | head -20
# Expected: JSON with results from Tripitaka
```

- [ ] **Step 3: Run verify_cloud_assets against production URL**

```bash
SERVICE_URL=$(gcloud run services describe namo-backend \
  --region=asia-southeast1 --project=namo-classroom \
  --format="value(status.url)")

NAMO_BASE_URL=$SERVICE_URL python -X utf8 scripts/verify_cloud_assets.py
# Expected: ALL CHECKS PASSED — Production Ready
```

- [ ] **Step 4: Commit final state**

```bash
git add -A
git commit -m "feat: [P21] Cloud Run deploy — namo-backend live on asia-southeast1"
```

---

## Task 10: Point Cloudflare DNS to Cloud Run

- [ ] **Step 1: Map custom domain to Cloud Run service**

```bash
gcloud run domain-mappings create \
  --service=namo-backend \
  --domain=api.namonexus.com \
  --region=asia-southeast1 \
  --project=namo-classroom
# Expected: DNS records to add in Cloudflare console
```

- [ ] **Step 2: Add CNAME in Cloudflare**

In Cloudflare dashboard for `namonexus.com`:
- Add **CNAME** record: `api` → `ghs.googlehosted.com`
- Proxy status: **DNS only** (grey cloud) — Cloud Run manages its own TLS

- [ ] **Step 3: Verify domain routing**

```bash
# Wait ~5 min for DNS propagation
curl -s https://api.namonexus.com/health | python -m json.tool
# Expected: {"status": "ok"}
```

---

## Rollback Plan

If deploy fails or health check fails:

```bash
# Rollback to previous revision
gcloud run services update-traffic namo-backend \
  --to-revisions=PREVIOUS=100 \
  --region=asia-southeast1 \
  --project=namo-classroom
```

---

## Environment Variables Reference (Cloud Run)

| Variable | Source | Value |
|---|---|---|
| `NAMO_ENV` | env var | `production` |
| `NAMO_DATABASE_URL` | env var | `postgresql+psycopg2://...?host=/cloudsql/...` |
| `NAMO_JWT_SECRET_KEY` | Secret Manager | `namo-jwt-secret:latest` |
| `NAMO_ADMIN_PASSWORD` | Secret Manager | `namo-admin-password:latest` |
| `NAMO_REASONING_API_KEY` | Secret Manager | `namo-groq-api-key:latest` |
| `NAMO_REDIS_URL` | Secret Manager | `namo-redis-url:latest` |
| `NAMO_ALLOWED_ORIGINS` | env var | `https://namonexus.com,https://www.namonexus.com` |
| `GOOGLE_CLOUD_PROJECT` | env var | `namo-classroom` |
| `UVICORN_WORKERS` | env var | `2` |
