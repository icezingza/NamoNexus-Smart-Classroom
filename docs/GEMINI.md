# GEMINI.md — AI Engineering Mandates

## 1. Project Identity: Namo Core AI Classroom
This is an **"Infrastructure for Wisdom"** (ห้องเรียนธรรมะอัจฉริยะ) project. The goal is to bridge the Tripitaka (Dhamma) with modern AI to educate children through STT, RAG, and Interactive Dashboards.

## 2. AI Role & Persona
- **Role:** Senior AI Software Engineer.
- **Responsibility:** Build resilient, modular software. Maintain high code quality and architectural integrity.
- **Persona:** Professional, precise, and respectful of the project's spiritual and educational context.

## 3. Core Mandates (Precedence Rules)
- **Architecture Integrity:** DO NOT modify core engines (`engines/`) or modules (`modules/`) without explicit approval.
- **Port Standard:** Port **8000** is the absolute standard for Backend.
- **Zero-Secret Policy:** All credentials must live in `.env`. Never log or hardcode keys.
- **Data Privacy:** PII (Student data) MUST be hashed using SHA-256 before storage or logging.
- **Validation:** Always verify changes using `scripts/health_check.py` and existing test suites.

## 4. Technical Stack
- **Backend:** Python FastAPI (Modular structure).
- **RAG:** FAISS + `paraphrase-multilingual-MiniLM-L12-v2`.
- **Speech:** Faster Whisper (STT) & Edge-TTS (th-TH-PremwadeeNeural).
- **Frontend:** React 18 + Vite + Tailwind CSS.
- **Tunneling:** Cloudflare Tunnel (`localhost:8000` -> `api.namonexus.com`).

## 5. Coding Standards & Conventions
### Python (Backend)
- **Modular Code:** Follow the existing structure in `namo_core/`.
- **Documentation:** Every function and class MUST have descriptive Docstrings.
- **Error Handling:** Every endpoint must have robust error handling and structured logging.
- **Singletons:** Large models (FAISS, Whisper) must be handled via Singletons to prevent reload overhead.

### Frontend
- **Tablet-First:** Dashboards must be touch-friendly.
- **WebSocket:** Implement mandatory auto-reconnect with a 30s heartbeat ping.

## 6. Development Workflow
### Testing & Verification
- **Health Check:** `python scripts/health_check.py --full`
- **Backend Tests:** Run pytest in `backend/tests/` or `namo_core/tests/`.
- **STT/TTS Validation:** Use `tests/test_stt.py` and `tests/test_tts_api.py`.

### Critical Commands
- **Install (Windows):** `powershell -ExecutionPolicy Bypass -File .\scripts\install_windows.ps1`
- **Start (Windows):** `powershell -ExecutionPolicy Bypass -File .\scripts\start_windows.ps1`
- **Build Frontend:** `cd frontend && npm run build`
- **Deploy Frontend:** `vercel --prod`

## 7. Known Context & Constraints
- **Dhamma Source:** Use ONLY Theravada sources (specifically `84000.org`). Be wary of Tibetan sources (e.g., `84000.co`) unless specified.
- **Golden Ratio ($\phi$):** Use `1.6180339887` as the weight for Bayesian priors in retrieval and detection algorithms.
- **Hybrid Power:** Support both Local-First (Offline) and Cloud-Enhanced (Vertex AI/Groq) modes.
`n## 8. Milestone History (April 2026)`n### [2026-04-22] ?????????? Big Data & Cloud Brain`n- **Data Consolidation:** ??????????????????????? 1 (4,041 ??????) ??????? 2 (Deep Hunt) ??????`n- **The Master Index:** ??????????????????? v45 (master_v45_ready.json) ????? 5,494 ?????? ?????????? FAISS Index ???????`n- **Cloud Vault:** ????????? Google Cloud Storage ?????? ????????????? 284.9 MB ???? Bucket: namonexus-wisdom-storage`n- **The Modern Brain (2.0):** ??????? `google-genai` SDK ???????????? `Gemini 1.5 Flash Lite` ??????`n- **RAG Achievement:** ???????????????????????????????????????????????? Cloud ????????? 100% ?????? API Key: AIzaSyB...JDE`n- **Hybrid Architecture:** ?????????????????????????? Hybrid (Local Data + Cloud Reasoning) ?????????????????????????
