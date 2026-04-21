# 🌐 OneDrive Deployment Plan
**Phase:** 3 | **Status:** ⏳ Ready to Execute | **Timeline:** ~2 hours

---

## 📋 Objective

Deploy Namo Core API + Frontend to OneDrive เพื่อเตรียมความพร้อมของสภาพแวดล้อมสำหรับการใช้งานจริง (Production-Ready Environment Preparation)

---

## ✅ Pre-Deployment Checklist

### Backend Ready
- [x] Lazy-loading implemented ✅
- [x] Memory leak fixed ✅
- [x] Stress tests passed ✅
- [x] Watchdog monitoring ready ✅
- [x] .env configured for production

### Frontend Ready
- [x] React 18 + Vite built
- [x] WebSocket handlers ready
- [x] Device selection implemented
- [x] Language toggle ready
- [x] Settings management ready

### Documentation Complete
- [x] DEPLOYMENT_READINESS.md ✅
- [x] VERIFICATION_CHECKLIST.md ✅
- [x] All technical guides ✅

---

## 🎯 OneDrive Deployment Structure

```
OneDrive/
├── namo-core-backend/          ← Backend source + .env
│   ├── backend/
│   ├── scripts/
│   ├── .env.production         ← Production configuration
│   ├── requirements.txt
│   └── README.md
│
├── namo-core-frontend/         ← Frontend build
│   ├── dist/                   ← Vercel deployment
│   ├── src/
│   ├── package.json
│   └── README.md
│
├── namo-docs/                  ← Documentation
│   ├── DEPLOYMENT_READINESS.md
│   ├── 403_FIX_GUIDE.md       ← Next phase
│   ├── WATCHDOG_SETUP.md
│   └── CLASSROOM_SETUP.md
│
└── namo-scripts/               ← Deployment scripts
    ├── deploy_backend.ps1
    ├── deploy_frontend.sh
    ├── setup_env.ps1
    └── verify_deployment.ps1
```

---

## 📦 Package Contents

### Backend Package
```
Files to backup:
├── backend/namo_core/services/orchestrator.py    (lazy-loading)
├── backend/namo_core/api/app.py                  (FastAPI)
├── backend/namo_core/api/auth.py                 (JWT middleware)
├── backend/namo_core/api/routes/                 (all endpoints)
├── .env.example                                   (template)
├── .env.production                                (production config)
├── requirements.txt                               (dependencies)
├── scripts/                                       (deployment scripts)
└── knowledge/tripitaka/                          (FAISS index)
```

### Frontend Package
```
Files to backup:
├── frontend/dist/                     (built app)
├── frontend/src/                      (source)
├── frontend/package.json              (dependencies)
├── frontend/.env.production           (config)
└── frontend/vercel.json               (Vercel config)
```

---

## 🔧 OneDrive Setup Steps

### Step 1: Create OneDrive Structure (5 minutes)

Create folders on OneDrive:
```
📁 Namo Core Project
  📁 Backend
  📁 Frontend  
  📁 Documentation
  📁 Scripts
  📁 Backups
```

### Step 2: Upload Backend (10 minutes)

```powershell
# Navigate to project
cd "C:\Users\icezi\Downloads\Github repo\namo_core_project"

# Create backup package
$backupName = "namo-backend-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
mkdir $backupName

# Copy essential files
Copy-Item -Path "backend\" -Destination "$backupName\backend" -Recurse
Copy-Item -Path "scripts\" -Destination "$backupName\scripts" -Recurse
Copy-Item -Path ".env.example" -Destination "$backupName\.env.example"
Copy-Item -Path "requirements.txt" -Destination "$backupName\requirements.txt"
Copy-Item -Path "DEPLOYMENT_READINESS.md" -Destination "$backupName\README.md"

# Compress
Compress-Archive -Path $backupName -DestinationPath "$backupName.zip"

# Upload to OneDrive/Backend/
# (Manual via Windows File Explorer or rclone)
```

### Step 3: Upload Frontend (5 minutes)

```powershell
# Navigate to frontend
cd "C:\Users\icezi\Downloads\Github repo\namo_core_project\frontend"

# Build if needed
npm run build

# Create backup
$backupName = "namo-frontend-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
mkdir $backupName
Copy-Item -Path "dist" -Destination "$backupName\dist" -Recurse
Copy-Item -Path "src" -Destination "$backupName\src" -Recurse
Copy-Item -Path "package.json" -Destination "$backupName\package.json"

# Compress
Compress-Archive -Path $backupName -DestinationPath "$backupName.zip"

# Upload to OneDrive/Frontend/
```

### Step 4: Upload Documentation (5 minutes)

Copy all .md files to OneDrive/Documentation/:
- DEPLOYMENT_READINESS.md
- VERIFICATION_CHECKLIST.md
- MEMORY_LEAK_FIX.md
- STRESS_TEST_ANALYSIS.md
- ACTIVATION_SUMMARY.md
- READY_FOR_VERIFICATION.md

### Step 5: Create Setup Scripts (5 minutes)

Upload to OneDrive/Scripts/:
- register_watchdog_startup.ps1
- namo_start_backend.ps1
- run_stress_test.ps1
- health_check.py

---

## 🔐 Production .env Template

**File: .env.production** (to upload with backend)

```bash
# Production Configuration
ENVIRONMENT=production
DEBUG=false

# API Server
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# CORS & Origins
ALLOWED_ORIGINS=namonexus.com,api.namonexus.com,classroom.namonexus.com

# Reasoning/LLM (Update with production credentials)
NAMO_REASONING_PROVIDER=openai-compatible
NAMO_REASONING_API_BASE_URL=https://api.groq.com/openai/v1
NAMO_REASONING_API_KEY=<YOUR_GROQ_API_KEY>
NAMO_REASONING_MODEL=llama-3.3-70b-versatile

# STT (Speech-to-Text)
NAMO_SPEECH_PROVIDER=faster-whisper
NAMO_SPEECH_MODEL=base

# TTS (Text-to-Speech)
NAMO_TTS_PROVIDER=edge-tts
NAMO_TTS_VOICE=th-TH-PremwadeeNeural

# Knowledge/RAG
NAMO_KNOWLEDGE_PROVIDER=faiss
NAMO_KNOWLEDGE_INDEX_PATH=knowledge/tripitaka/tripitaka_index.faiss

# Cloudflare Tunnel
CLOUDFLARE_TUNNEL_URL=https://api.namonexus.com

# Security
JWT_SECRET_KEY=<GENERATE_SECURE_KEY>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090

# Database (if needed)
DATABASE_URL=sqlite:///./namo_core.db

# Feature Flags
ENABLE_CLASSROOM=true
ENABLE_EMOTION_DETECTION=true
ENABLE_WATCHDOG=true
```

---

## 📊 Deployment Verification

After uploading to OneDrive, verify:

```powershell
# 1. Check file integrity
Get-FileHash "$backupName.zip"

# 2. Verify structure
Expand-Archive "$backupName.zip" -DestinationPath ".\verify\"
dir ".\verify\$backupName\backend"

# 3. Check critical files exist
Test-Path ".\verify\$backupName\backend\namo_core\services\orchestrator.py"
Test-Path ".\verify\$backupName\scripts\namo_start_backend.ps1"
Test-Path ".\verify\$backupName\.env.example"
```

**Expected:** All paths return True ✅

---

## 🔄 Next Phase: 403 Fix

Once OneDrive backup complete:

### Phase 4: Fix 403 Forbidden Errors
**Goal:** Configure proper authentication for Classroom endpoints

**Tasks:**
1. Analyze 403 errors from stress test
2. Implement JWT token validation
3. Configure CORS headers correctly
4. Setup authentication flow for frontend
5. Test end-to-end authentication
6. Deploy with proper auth enabled

---

## 📋 OneDrive Deployment Checklist

### Pre-Upload
- [ ] Backend files organized
- [ ] Frontend built (dist/)
- [ ] .env.production created
- [ ] Documentation compiled
- [ ] Scripts ready

### Upload
- [ ] Backend package uploaded
- [ ] Frontend package uploaded
- [ ] Documentation uploaded
- [ ] Scripts uploaded
- [ ] Backup verified

### Post-Upload
- [ ] Files integrity checked
- [ ] Directory structure verified
- [ ] README files in each folder
- [ ] Deployment guide accessible
- [ ] OneDrive link shared (if needed)

### Documentation
- [ ] OneDrive setup guide created
- [ ] Restore instructions written
- [ ] Authentication setup documented
- [ ] Deployment procedures documented
- [ ] Troubleshooting guide included

---

## 🎯 Success Criteria

✅ OneDrive deployment complete when:
- Backend source backed up with lazy-loading
- Frontend build backed up
- All documentation accessible
- Production .env template ready
- Deployment scripts included
- Verification passed

---

## ⏱️ Timeline

| Step | Task | Duration | Total |
|------|------|----------|-------|
| 1 | Create OneDrive structure | 5 min | 5 min |
| 2 | Upload backend | 10 min | 15 min |
| 3 | Upload frontend | 5 min | 20 min |
| 4 | Upload documentation | 5 min | 25 min |
| 5 | Upload scripts | 5 min | 30 min |
| 6 | Verify integrity | 10 min | 40 min |
| 7 | Create restore guide | 20 min | 60 min |
| **Total** | | | **~1 hour** |

---

## 🚀 After OneDrive Deployment

### Ready for:
1. ✅ **Phase 4: 403 Fix** (authentication)
2. ✅ **Phase 5: Classroom Deployment** (students + teachers)
3. ✅ **Production Monitoring** (daily checks)
4. ✅ **Scaling & Optimization** (performance tuning)

---

## 📞 Deployment Support

**If you need to restore from OneDrive:**

```powershell
# 1. Download backup from OneDrive
# 2. Extract zip file
Expand-Archive -Path "namo-backend-20260421-105930.zip" -DestinationPath "."

# 3. Copy to production location
Copy-Item -Path ".\namo-backend-20260421-105930\backend" -Destination "C:\production\namo_core" -Recurse

# 4. Setup environment
Copy-Item -Path ".\namo-backend-20260421-105930\.env.example" -Destination "C:\production\.env.production"

# 5. Restart backend
powershell -File "C:\production\scripts\namo_start_backend.ps1"
```

---

**Status:** ✅ READY FOR ONEDRIVE DEPLOYMENT

Next Command: Upload files to OneDrive as outlined above, then proceed to Phase 4: 403 Fix

