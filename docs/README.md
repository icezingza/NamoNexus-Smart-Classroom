# Namo Core — AI Dhamma Classroom System

> ห้องเรียนธรรมะอัจฉริยะ — Smart Dhamma Classroom powered by AI

ระบบ AI สำหรับห้องเรียนพระพุทธศาสนา ผสาน Whisper (STT), FAISS (RAG), LLM, Edge-TTS,
Emotion Engine และระบบควบคุมห้องเรียนเข้าด้วยกันในวงจรเดียว

---

## Project Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Foundation — Architecture & folder structure | ✅ Complete |
| 1 | Core Architecture — Orchestrator, Engines, Modules | ✅ Complete |
| 2 | Knowledge System — FAISS + Tripitaka RAG | ✅ Complete |
| 3 | Audio System — Whisper STT + Edge-TTS | ✅ Complete |
| 4 | AI Reasoning — NamoNexus Loop (STT→RAG→LLM→TTS) | ✅ Complete |
| 5 | Emotion Engine — Multi-signal student state detection | ✅ Complete |
| 6 | Classroom System — Slides, students, events, state machine | ✅ Complete |
| 7 | Integration — Unified ClassroomPipeline | ✅ Complete |
| 8 | Deployment — Scripts, health check, production config | ✅ Complete |

---

## Quick Start

### Windows (School Server / NAS)

```powershell
# 1. One-time setup
powershell -ExecutionPolicy Bypass -File .\scripts\install_windows.ps1

# 2. Edit configuration
notepad .env

# 3. Start the system
powershell -ExecutionPolicy Bypass -File .\scripts\start_windows.ps1

# 4. Verify everything is working
python scripts/health_check.py --full

# 5. Stop
powershell -ExecutionPolicy Bypass -File .\scripts\stop_windows.ps1
```

### Linux / NAS (Synology, Raspberry Pi, Ubuntu)

```bash
# 1. One-time setup
chmod +x scripts/*.sh && ./scripts/install_linux.sh

# 2. Edit configuration
nano .env

# 3. Start the system
./scripts/start_linux.sh

# 4. Verify everything is working
python3 scripts/health_check.py --full

# 5. Stop
./scripts/stop_linux.sh
```

---

## Project Layout

```
namo_core_project/
├── .env.example              # Environment configuration template
├── CLAUDE.md                 # AI assistant project rules
├── README.md                 # This file
│
├── namo_core/                # FastAPI backend
│   ├── api/routes/           # HTTP endpoints (11 routers)
│   │   ├── nexus.py          # /nexus/* — full pipeline endpoints
│   │   ├── emotion.py        # /emotion/* — Phase 5
│   │   ├── classroom.py      # /classroom/* — Phase 6
│   │   └── ...
│   ├── engines/              # Signal processing engines
│   │   ├── empathy/          # EmpathyEngine (tone + teaching_hint)
│   │   ├── resonance/        # ResonanceEngine (3-signal score)
│   │   └── namonexus/        # Intent classifier
│   ├── modules/              # Hardware/software adapters
│   │   ├── emotion/          # EmotionDetector (Phase 5)
│   │   ├── speech/           # Whisper STT
│   │   └── tts/              # Edge-TTS providers
│   ├── services/
│   │   ├── integration/      # ClassroomPipeline (Phase 7)
│   │   ├── emotion/          # EmotionService + StateTracker
│   │   ├── classroom/        # SlideContentService, StudentTracker, EventLog
│   │   ├── knowledge/        # FAISS RAG + ContextBuilder
│   │   └── reasoning/        # LLM provider abstraction
│   ├── knowledge/            # Curriculum data
│   │   ├── lessons/          # 8 lesson plans
│   │   ├── materials/        # Dhamma markdown files
│   │   └── tripitaka/        # Sample suttas JSON
│   └── main.py               # uvicorn entry point
│
├── dashboard/                # React 18 + Vite frontend
│
├── scripts/
│   ├── install_windows.ps1   # Windows one-time setup
│   ├── install_linux.sh      # Linux/NAS one-time setup
│   ├── start_windows.ps1     # Start (Windows)
│   ├── start_linux.sh        # Start (Linux/NAS)
│   ├── stop_windows.ps1      # Stop (Windows)
│   ├── stop_linux.sh         # Stop (Linux/NAS)
│   ├── health_check.py       # System readiness check
│   └── backup_project.ps1    # Source backup
│
└── roadmap/                  # Architecture docs
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| GET | `/status` | Full pipeline snapshot |
| POST | `/nexus/text-chat` | **Main endpoint** — Text → full pipeline → response |
| POST | `/nexus/classroom-loop` | Live classroom interaction loop |
| POST | `/nexus/voice-chat` | Audio file → STT → full pipeline |
| GET | `/emotion/state` | Current student emotion state |
| POST | `/classroom/session/start` | Start lesson session |
| POST | `/classroom/session/end` | End session |
| GET | `/classroom/slide/content` | Current slide content |
| POST | `/classroom/student/connect` | Student joins |
| GET | `/classroom/events` | Event log |
| GET | `/classroom/lessons` | Available lessons |
| POST | `/reasoning/explain` | LLM explanation (with emotion adapt) |
| GET | `/knowledge/search` | Dhamma knowledge search |

Interactive docs: `http://localhost:8000/docs`

---

## Configuration

Copy `.env.example` to `.env` and edit as needed:

```bash
# Key settings for production classroom:
NAMO_ENV=production
NAMO_API_HOST=0.0.0.0          # Allow LAN access
NAMO_SPEECH_PROVIDER=whisper-local
NAMO_SPEECH_MODEL=small
NAMO_TTS_PROVIDER=edge-tts
NAMO_TTS_VOICE=th-TH-PremwadeeNeural

# For real LLM (optional — works with mock by default):
NAMO_REASONING_PROVIDER=openai-compatible
NAMO_REASONING_API_BASE_URL=http://localhost:1234/v1
NAMO_REASONING_API_KEY=lm-studio
```

---

## Classroom Pipeline (Phase 7)

```
Student speaks / types
    |
[P5] EmotionService   -> composite_score, smoothed_state
    |
[P5] EmpathyEngine    -> tone + teaching_hint (Thai)
    |
[P6] SlideController  -> current slide dhamma_point
    |
[P4] KnowledgeService -> FAISS RAG search
    |
ContextBuilder        -> hint + slide + knowledge
    |
[P4] ReasoningService -> LLM adapted response
    |
[P6] EventLog         -> log + state transition
    |
[P3] SpeechSynthesizer -> TTS audio (optional)
```

---

## Backup

```powershell
# Windows — create backup before classroom session
powershell -ExecutionPolicy Bypass -File .\scripts\backup_project.ps1 -Label "pre-session"
```

Backups are saved to `backups/` (excluded from git).

---

## Tech Stack

- **Backend:** Python 3.10+ · FastAPI · uvicorn
- **Semantic Search:** FAISS · sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`)
- **Speech-to-Text:** openai-whisper (local)
- **Text-to-Speech:** edge-tts (`th-TH-PremwadeeNeural`)
- **LLM:** OpenAI-compatible API (LM Studio / Ollama / OpenAI)
- **Frontend:** React 18 · Vite · Tailwind CSS
- **Deployment:** Windows Server / Linux NAS (no Docker required)
