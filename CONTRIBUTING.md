# Contributing to NamoNexus Smart Classroom

ขอบคุณที่สนใจร่วมพัฒนา **NamoNexus Resonance Engine (NRE)** — ระบบห้องเรียนธรรมะอัจฉริยะที่ขับเคลื่อนด้วย AI และ Theravada Tripitaka Knowledge Base

---

## 🧭 ก่อนเริ่มต้น

โปรดอ่าน [README.md](./README.md) และทำความเข้าใจ Project Mental Model ก่อน:

- **Backend**: FastAPI (Async 100%) — Port `8000`
- **Frontend**: React 18 + Vite — Port `5173`
- **Knowledge Base**: FAISS + RAG Pipeline (Tripitaka, 168,861 vectors)
- **Cloud**: GCP (`namo-classroom`, region `asia-southeast1`)

---

## 🏗️ Architecture Overview

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

---

## ⚙️ Development Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- Redis (local หรือ Memorystore)
- GCP credentials (ผ่าน Secret Manager เท่านั้น — ห้าม hardcode)

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn namo_core.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Health Check
```bash
python scripts/health_check.py
# ควรผ่าน 16/16 checks
```

---

## 📐 Coding Standards & Architectural Rules

กฎเหล็กที่ต้องปฏิบัติตามเสมอ:

| Rule | Detail |
|---|---|
| **Async Integrity** | ห้ามใช้ blocking sync I/O ใน FastAPI endpoint ใหม่เด็ดขาด ใช้ `asyncio.to_thread` หรือ `aiofiles` |
| **Secret Security** | ห้าม hardcode connection string หรือ credentials ทุกกรณี ดึงผ่าน GCP Secret Manager เท่านั้น |
| **Fallback Logic** | WebSocket ต้องมีระบบ fallback เป็น HTTP Polling เมื่อสัญญาณหลุด (Graceful Degradation) |
| **RAG Quality Gate** | ก่อน embed ข้อมูล Tripitaka รอบใหม่ ต้องผ่าน Hard/Soft filter ใน `scripts/tripitaka_quality_filter.py` หรือ audit ที่เทียบเท่าเสมอ |
| **Port Standard** | Backend `8000`, Frontend Local `5173` — ห้ามเปลี่ยนโดยไม่มีเหตุผล |

---

## 🌿 Branching Strategy

```
main          → production-ready เท่านั้น
feature/*     → ฟีเจอร์ใหม่ (เช่น feature/notebook-quiz-mode)
fix/*         → bug fix (เช่น fix/status-endpoint-500)
phase/*       → งานตาม Phase (เช่น phase/p11q-quality-filter)
chore/*       → งาน infra/config/docs
```

---

## 📝 Commit Message Convention

ใช้รูปแบบ [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>
```

### Types
| Type | ใช้เมื่อ |
|---|---|
| `feat` | เพิ่มฟีเจอร์ใหม่ |
| `fix` | แก้ไข bug |
| `chore` | งาน config, dependency, infra |
| `docs` | แก้ไขเอกสาร |
| `refactor` | ปรับโครงสร้างโค้ดโดยไม่เปลี่ยน behavior |
| `test` | เพิ่ม/แก้ไข test |
| `perf` | ปรับปรุง performance |

### ตัวอย่าง
```
feat(notebook): add quiz mode with 5 question types
fix(status): convert status() to async to resolve HTTP 500
chore(security): add gcs key files to .gitignore
perf(faiss): implement lazy-loading to fix 949MB memory leak
```

---

## 🔍 Knowledge Base Contributions

หากต้องการแก้ไขหรือ rebuild Tripitaka index:

1. รัน audit ก่อนเสมอ:
   ```bash
   python scripts/audit_knowledge_vectors.py
   ```

2. ใช้ filter module ก่อน embed:
   ```bash
   python scripts/master_ingestion.py --dry-run   # ตรวจสอบก่อน
   python scripts/master_ingestion.py             # รัน ingestion จริง
   ```

3. ตรวจสอบ vector count หลัง rebuild — ค่า baseline ปัจจุบันคือ **168,861 vectors**
   - ตัวเลข `162,895` เป็น legacy reference ในเอกสารเก่า ไม่ใช่ค่าปัจจุบัน

---

## 🔐 Security Guidelines

- **ห้าม** commit ไฟล์ `.json` ที่เป็น GCP service account key
- **ห้าม** hardcode IP address, password, หรือ API key ในโค้ด
- Secrets ทั้งหมดต้องดึงผ่าน `backend/namo_core/utils/gcp_secrets.py`
- ตรวจสอบ `.gitignore` ก่อน commit ทุกครั้งหากมีไฟล์ credentials ใหม่

---

## 🚀 Merge Request Process

1. Fork หรือสร้าง branch จาก `main`
2. เขียนโค้ดตาม Architectural Rules ด้านบน
3. รัน health check: `python scripts/health_check.py` — ต้องผ่าน 16/16
4. เขียน commit message ตาม Conventional Commits
5. เปิด Merge Request พร้อมอธิบาย:
   - **What**: เปลี่ยนแปลงอะไร
   - **Why**: เหตุผล
   - **Impact**: กระทบส่วนไหนบ้าง (โดยเฉพาะ FAISS index, Redis, หรือ WebSocket)
6. รอ review จาก Project Owner (@icezingza)

---

## 📬 Contact

- **Project Owner**: พี่ไอซ์ (P'Ice) — Tech Monk & AI Architect
- **Repository**: [gitlab.com/namonexus2/NamoNexus-Smart-Classroom](https://gitlab.com/namonexus2/NamoNexus-Smart-Classroom)
