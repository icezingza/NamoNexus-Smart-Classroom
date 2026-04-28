# NamoNexus Smart Classroom 🧠
### NamoNexus Resonance Engine (NRE) v5.0.0 — Sovereign Edition

> “Infrastructure แห่งปัญญา — Bridging Theravada Wisdom with Modern AI”

[![Version](https://img.shields.io/badge/Version-5.0.0%20Sovereign-gold)]()
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)]()
[![Health](https://img.shields.io/badge/Health%20Check-16%2F16%20Passed-brightgreen)]()
[![FAISS](https://img.shields.io/badge/FAISS-168%2C861%20vectors-blue)]()
[![License](https://img.shields.io/badge/License-Proprietary-red)]()

---

## 🏗️ Architecture: The Wisdom Stream Flow

```text
[ Teacher Tablet ]          [ Student Display ]
       ↓                           ↑
[ www.namonexus.com ]  ←── (WebSocket wss://)
       ↓
[ Cloudflare Tunnel ]  (Zero Trust, api.namonexus.com)
       ↓
[ Lenovo Local Server :8000 ]
  ├── FastAPI (Async 100%)
  ├── Redis       (State / PubSub, Latency < 50ms)
  ├── PostgreSQL  (Persistent Layer)
  └── FAISS       (Tripitaka Index, 168,861 vectors)
         ↑
Google Cloud Platform (asia-southeast1)
  ├── Cloud SQL       (PostgreSQL managed)
  ├── Memorystore     (Redis managed)
  ├── Secret Manager  (All credentials)
  └── GCS Bucket      gs://namo-classroom-models/
```

---

## 🎯 Hybrid Cloud Strategy

| Layer | Technology | Purpose |
|---|---|---|
| **Source Code** | GitLab (this repo) | Version control, CI/CD, rollback |
| **Large Models** | GCS `namo-classroom-models` | FAISS index (239 MB), training data |
| **Secrets** | GCP Secret Manager | Zero hardcode — zero credential risk |
| **Frontend** | React 18 + Vite (`namonexus.com`) | Dual-screen: `/teacher` และ `/display` |
| **Backend** | Lenovo + Cloudflare Tunnel | Low-latency, offline-capable |

---

## 🧠 AI Stack

| Component | Technology | Detail |
|---|---|---|
| **LLM** | Groq `llama-3.3-70b-versatile` | OpenAI-compatible API |
| **STT** | FasterWhisper `base` | Thai language optimized |
| **TTS** | Edge TTS `th-TH-PremwadeeNeural` | Microsoft Neural Voice |
| **RAG** | FAISS IndexFlatIP (cosine) | 168,861 vectors, dim=384 |
| **Embeddings** | `paraphrase-multilingual-MiniLM-L12-v2` | Multilingual sentence embeddings |
| **Emotion** | 5-state detector | focused → disengaged, Bayesian prior φ=1.618 |

---

## 📦 Repository Structure

```
NamoNexus-Smart-Classroom/
├── backend/namo_core/          ← FastAPI server (Async 100%)
│   ├── api/                    ← Routes, JWT auth, WebSocket
│   ├── config/settings.py      ← GCP Secret Manager wiring
│   ├── utils/gcp_secrets.py    ← Secret Manager client
│   ├── services/               ← Orchestrator (lazy-loading), RAG
│   ├── modules/                ← STT, TTS, Emotion, Classroom
│   └── engines/                ← NamoNexus loop, Empathy, Fusion
├── frontend/                   ← React 18 + TypeScript + Shadcn UI
│   └── src/                    ← /teacher และ /display dual-screen routing
├── scripts/
│   ├── health_check.py         ← 16/16 runtime checks
│   ├── audit_knowledge_vectors.py  ← FAISS quality audit
│   ├── tripitaka_quality_filter.py ← Hard/Soft filter module
│   ├── master_ingestion.py     ← Ingestion entrypoint + --dry-run
│   └── upload_to_gcs.py        ← GCS sync + MD5 integrity check
├── docs/                       ← Architecture, deployment guides
├── CHANGELOG.md
├── CONTRIBUTING.md
└── requirements.txt
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Redis (local หรือ GCP Memorystore)
- GCP credentials ผ่าน Secret Manager

### Backend
```bash
# 1. Clone
git clone https://gitlab.com/namonexus2/NamoNexus-Smart-Classroom.git
cd NamoNexus-Smart-Classroom

# 2. Setup
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Download models from GCS
python scripts/upload_to_gcs.py

# 4. Run
uvicorn backend.namo_core.main:app --host 0.0.0.0 --port 8000 --reload

# 5. Health check
python scripts/health_check.py  # ควรผ่าน 16/16
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# เปิด http://localhost:5173/teacher
```

---

## 📊 Phase Completion (Snapshot: 2026-04-27)

| Phase | Description | Status |
|---|---|---|
| P0–8 | Foundation → Deployment Scripts | ✅ Complete |
| P9 | Cloudflare Tunnel + Public WSS (`api.namonexus.com`) | ✅ Complete |
| P10 | Dual-Screen Frontend (`/teacher` และ `/display`) | ✅ Complete |
| P11Q | Tripitaka Quality Audit + Hard/Soft Filter Layer | ✅ Complete |
| P12 | SQLite + SemanticCache + Script Path Fixes | ✅ Complete |
| P13 | Enterprise Auth (JWT Middleware + Sovereign Bypass) | ✅ Complete |
| P2 | Deep Async Refactor (Backend 100% Async) | ✅ Complete |
| P3 | Persistent Layer (Redis ✅, PostgreSQL/Cloud SQL ⚠️ Transitional) | ⚠️ Transitional |
| P4 | Notebook System — Saturate Wisdom | ✅ Complete |
| LAN | Vite Network + CORS + Heartbeat Stability | ✅ Complete |
| SEC | GCP Secret Manager Integration | ✅ Complete (code-level) |
| OPS | Local Runtime Health Check (16/16) | ✅ Complete |

---

## 🔬 Knowledge Base: Theravada Tripitaka

| Metric | Value |
|---|---|
| FAISS Index | `knowledge/tripitaka_main/tripitaka_index.faiss` |
| Total Vectors | **168,861** (dim=384) |
| Index Size | ~239 MB |
| Average Chunk Length | 619.25 characters |
| Empty / HTML Leak Chunks | 0 / 0 |
| Hard-dropped Records | 451 |
| Soft-merged Fragments | 1,496 |

> ⚠️ ตัวเลข `162,895` เป็น legacy reference ในเอกสารเก่า — ค่าปัจจุบันคือ **168,861 vectors**

---

## 🌐 Live Endpoints

| Service | URL | Status |
|---|---|---|
| Frontend | https://namonexus.com | ✅ Live |
| API Gateway | https://api.namonexus.com | ✅ Live |
| Teacher Dashboard | https://namonexus.com/teacher | ✅ Live |
| Student Display | https://namonexus.com/display | ✅ Live |
| Models Storage | `gs://namo-classroom-models/` | ✅ Synced |

---

## 🛡️ Architectural Rules (v5.0.0)

| Rule | Detail |
|---|---|
| **Async Integrity** | ห้ามใช้ blocking sync I/O ใน endpoint ใหม่ — ใช้ `asyncio.to_thread` / `aiofiles` |
| **Secret Security** | ห้าม hardcode credentials — ดึงผ่าน GCP Secret Manager เท่านั้น |
| **Fallback Logic** | WebSocket ต้องมี HTTP Polling fallback (Graceful Degradation) |
| **RAG Quality Gate** | ต้องผ่าน Hard/Soft filter ก่อน embed Tripitaka รอบใหม่ทุกครั้ง |
| **Port Standard** | Backend `8000`, Frontend `5173` |

---

## 💬 Contributing

อ่าน [CONTRIBUTING.md](./CONTRIBUTING.md) สำหรับแนวทางการพัฒนา, branching strategy, commit convention และ security guidelines

---

*Built with ❤️ for Dhamma education — NamoNexus Team*
