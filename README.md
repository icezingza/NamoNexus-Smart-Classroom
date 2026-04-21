# NamoNexus Smart Classroom 🧠
### AI-Powered Dhamma Education System — Enterprise Edition

> "Bridging Ancient Wisdom with Modern Intelligence"

[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)]()
[![Phase](https://img.shields.io/badge/Phase-9--13%20Complete-blue)]()
[![License](https://img.shields.io/badge/License-Proprietary-red)]()

---

## 🏗️ Hybrid Cloud Architecture

```
Tablet Browser (Touch UI)
    ↓ HTTPS / WSS
namonexus.com  ←  React 18 + TypeScript + Tailwind (Vercel CDN)
    ↓ wss://
Cloudflare Tunnel (Public HTTPS/WSS — Zero Trust)
    ↓ localhost:8000
Lenovo Local Server  ←  FastAPI + FAISS RAG + Whisper STT
    ├── Whisper STT (faster-whisper)
    ├── FAISS Vector DB (162,895 vectors — Theravada Tripitaka)
    ├── EmotionEngine (5-state classroom monitoring)
    └── ClassroomPipeline (real-time teaching loop)
         ↑
Google Cloud Storage (Backup & Sync)
    └── gs://namo-classroom/
        ├── models/tripitaka_index.faiss   (239 MB)
        └── data/*.jsonl                   (7 knowledge sources)
```

## 🎯 Hybrid Cloud Strategy

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Source Code** | GitHub (this repo) | Version control, CI/CD, rollback |
| **Large Models** | Google Cloud Storage | FAISS index (239MB), training data |
| **Secrets** | Local `.env` only | Never pushed — zero credential risk |
| **Frontend** | Vercel CDN | Global static hosting, auto-deploy |
| **Backend** | Lenovo + Cloudflare | Low-latency, offline-capable |

> **Design Principle:** Keep compute local (latency), keep storage in the cloud (resilience),
> keep code in GitHub (collaboration).

---

## 🧠 AI Stack

- **LLM:** Groq `llama-3.3-70b-versatile` (OpenAI-compatible API)
- **STT:** FasterWhisper `base` model — Thai language optimized
- **TTS:** Microsoft Edge TTS `th-TH-PremwadeeNeural`
- **RAG:** FAISS IndexFlatIP (cosine) — 162,895 vectors, dim=384
- **Embeddings:** `paraphrase-multilingual-MiniLM-L12-v2`
- **Emotion:** 5-state detector (focused → disengaged) with Bayesian prior φ=1.618

---

## 📦 Repository Structure

```
NamoNexus-Smart-Classroom/
├── backend/namo_core/     ← FastAPI server (Phase 0-13)
│   ├── api/               ← Routes, auth (JWT), WebSocket
│   ├── services/          ← Orchestrator (lazy-loading), reasoning, RAG
│   ├── modules/           ← STT, TTS, emotion, classroom
│   └── engines/           ← NamoNexus loop, empathy, fusion
├── frontend/              ← React 18 + TypeScript + Shadcn UI
│   └── src/               ← Dashboard, Teacher Suite, hooks
├── scripts/               ← Watchdog, deploy, stress test, GCS upload
├── docs/                  ← Architecture, deployment, verification guides
└── requirements.txt
```

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/icezingza/NamoNexus-Smart-Classroom.git
cd NamoNexus-Smart-Classroom

# 2. Backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env   # fill in API keys

# 4. Download large models from GCS
python scripts/upload_to_gcs.py  # or pull from gs://namo-classroom/

# 5. Run
python backend/namo_core/main.py
```

---

## 🌐 Live Deployment

| Service | URL | Status |
|---------|-----|--------|
| Frontend | https://namonexus.com | ✅ Live |
| API | https://api.namonexus.com | ✅ Live |
| FAISS Knowledge | gs://namo-classroom/models/ | ✅ Synced |

---

## 📊 Phase Completion

| Phase | Description | Status |
|-------|-------------|--------|
| 0-8 | Foundation → Deployment Scripts | ✅ Complete |
| 9 | Cloudflare Tunnel + Public WSS | ✅ Complete |
| 10 | Tablet Dashboard (TypeScript) | ✅ Complete |
| 11 | FAISS Knowledge Expansion (162,895 vectors) | ✅ Complete |
| 12 | Local Audio + Speaker Diarization | 🔜 Planned |
| 13 | Classroom Analytics | ✅ Complete |

---

*Built with ❤️ for Dhamma education — NamoNexus Team*
