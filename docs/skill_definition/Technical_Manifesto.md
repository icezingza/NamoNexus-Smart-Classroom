# NamoNexus Sovereign Technical Manifesto (v5.0.0)

This document defines the core technical standards and architectural integrity of the NamoNexus Smart Classroom system.

## 1. System Architecture: NRE v5.0.0
- **Edition**: Sovereign Edition.
- **Infrastructure**: Hybrid Cloud stack (Lenovo Edge + GCP).
- **Core Orchestration**: `NamoOrchestrator` implements a multi-stage pipeline:
    1. **Perception**: Speech transcription + Vision analysis.
    2. **Intent**: `NamoNexusEngine` classifies student intent.
    3. **Fusion**: Combines signals from all inputs.
    4. **Resonance**: Calculates a 3-signal score (Attention, Sentiment, Engagement).
    5. **Emotion**: `EmotionService` smoothing and state detection.
    6. **Empathy**: Enriches payload with tone and `teaching_hint`.
    7. **Reasoning**: LLM generating responses adapted by `teaching_hint`.

## 2. Backend Protocol (FastAPI)
- **Engine**: FastAPI (Python 3.12+).
- **Integrity Rule**: 100% Async/Await. Strictly prohibit any blocking synchronous I/O.
- **WebSocket Protocol**: Event-driven updates via `/ws` using the following schema:
    ```json
    {
      "emotion": { "current": "serene", "intensity": 0.8, "visual_signal": "calm" },
      "classroom": { "active_students": 25, "noise_level": 15, "engagement_score": 0.92 },
      "reasoning": { "thinking": true, "step": "Retrieving Tripitaka context" },
      "transcript": { "text": "...", "speaker": "namo" },
      "ts": 1714652400
    }
    ```

## 3. Data & Storage
- **Knowledge Retrieval (RAG)**: 
    - **Engine**: FAISS (IndexFlatIP for Cosine Similarity).
    - **Model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
    - **Optimization**: Bayesian weighting using the Golden Ratio ($\phi \approx 1.618$) for score normalization.
    - **Diversity Filter**: Max 2 results per source category (learntripitaka, 84000_attha, jataka, etc.).
- **Caching**: Semantic caching for high-frequency query similarity matching.

## 4. Security & Secrets
- **Zero-Hardcode Policy**: All credentials MUST come from GCP Secret Manager.
- **Local Dev**: Use `.env` with strict `.gitignore` exclusion.
- **Authentication**: `EnterpriseAuthMiddleware` handles Bearer tokens for HTTP and query params for WebSockets.

## 5. Development Workflow
- **Commits**: Conventional Commits + JIRA issues.
- **Typing**: Python `pydantic` models for API schemas; TypeScript strict interfaces for frontend.
- **Lifecycle**: FastAPI lifespan events for pre-loading FAISS indices into RAM.
