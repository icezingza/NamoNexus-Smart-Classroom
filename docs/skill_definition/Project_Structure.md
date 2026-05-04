# NamoNexus Project Structure & Core Logic

This document provides a high-level map of the codebase to help the AI understand where things live.

## 1. Directory Map
- `/backend`: FastAPI source code.
    - `/namo_core`: Core logic (Reasoning, Knowledge, Emotion, TTS).
        - `/config`: Configuration and GCP secrets.
        - `/services`: Business logic and AI orchestrators.
- `/frontend`: React + Vite + TypeScript source code.
    - `/src/components`: UI components (Tailwind + Lucide).
    - `/src/hooks`: Custom hooks (useNamoSocket, useNamoSettings).
    - `/src/pages`: Main application views.
- `/knowledge`: Vector store indices (FAISS) and raw Dhamma data.
- `/scripts`: PowerShell automation for startup, deployment, and watchdog.
- `/docs`: Project documentation and Petty Patent drafts.

## 2. Core Service Singletons
The following services are managed as singletons in `app.state` to ensure performance:
- `NamoOrchestrator`: Coordinates Reasoning and Emotion engines.
- `KnowledgeService`: Manages the 168k FAISS vector index.
- `SpeechSynthesizer`: Handles Text-to-Speech via premium providers.

## 3. Real-time Communication
- **WebSocket**: Primary channel for real-time AI responses and transcriptions.
- **Path**: `/ws` (with token-based authentication).
- **Hooks**: `useNamoSocket` for managing state and event-driven updates.

## 4. Key Configurations
- `vite.config.ts`: Configured for host access and premium dev experience.
- `tailwind.config.js`: Contains custom theme tokens (colors, animations, border-radius).
- `requirements.txt` / `package.json`: Definitive list of dependencies.
