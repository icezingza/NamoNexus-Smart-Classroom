{
  "nodes": [
    {
      "id": "group-1",
      "type": "group",
      "position": { "x": 0, "y": 0 },
      "style": { "width": 550, "height": 400 },
      "data": { "label": "1. Fetch Issue" }
    },
    {
      "id": "prompt-ticket",
      "type": "prompt",
      "parentId": "group-1",
      "position": { "x": 20, "y": 50 },
      "data": { "label": "Please enter the GitHub Issue...", "name": "prompt-ticket" }
    },
    {
      "id": "prompt-gh-fetch",
      "type": "prompt",
      "parentId": "group-1",
      "position": { "x": 20, "y": 150 },
      "data": { "label": "Fetch the issue details from GitHub", "name": "prompt-gh-fetch" }
    },
    {
      "id": "prompt-fetch-failed",
      "type": "prompt",
      "parentId": "group-1",
      "position": { "x": 280, "y": 150 },
      "data": { "label": "Failed to fetch GitHub Issue", "name": "prompt-fetch-failed" }
    },
    {
      "id": "ask-retry-fetch",
      "type": "askUserQuestion",
      "parentId": "group-1",
      "position": { "x": 310, "y": 250 },
      "data": { "label": "Retry fetching issue?", "name": "ask-retry-fetch" }
    },
    {
      "id": "subagentflow-1778149813844",
      "type": "subagentflow",
      "parentId": "group-1",
      "position": { "x": 20, "y": 300 },
      "data": { "label": "subagentflow-1", "name": "subagentflow-1778149813844" }
    },
    {
      "id": "group-2",
      "type": "group",
      "position": { "x": 0, "y": 450 },
      "style": { "width": 550, "height": 280 },
      "data": { "label": "2. Confirm Understanding" }
    },
    {
      "id": "prompt-understanding",
      "type": "prompt",
      "parentId": "group-2",
      "position": { "x": 20, "y": 50 },
      "data": { "label": "Current Understanding", "name": "prompt-understanding" }
    },
    {
      "id": "ask-understanding",
      "type": "askUserQuestion",
      "parentId": "group-2",
      "position": { "x": 20, "y": 150 },
      "data": { "label": "Is this understanding correct?", "name": "ask-understanding" }
    },
    {
      "id": "prompt-clarify",
      "type": "prompt",
      "parentId": "group-2",
      "position": { "x": 300, "y": 150 },
      "data": { "label": "Clarification needed", "name": "prompt-clarify" }
    },
    {
      "id": "group-3",
      "type": "group",
      "position": { "x": 600, "y": 0 },
      "style": { "width": 550, "height": 350 },
      "data": { "label": "3. Reproduce" }
    },
    {
      "id": "ask-reproduce",
      "type": "askUserQuestion",
      "parentId": "group-3",
      "position": { "x": 20, "y": 50 },
      "data": { "label": "Would you like to reproduce?", "name": "ask-reproduce" }
    },
    {
      "id": "prompt-reproduce",
      "type": "prompt",
      "parentId": "group-3",
      "position": { "x": 20, "y": 150 },
      "data": { "label": "Reproduction steps", "name": "prompt-reproduce" }
    },
    {
      "id": "ask-reproduce-result",
      "type": "askUserQuestion",
      "parentId": "group-3",
      "position": { "x": 20, "y": 250 },
      "data": { "label": "Reproduction result?", "name": "ask-reproduce-result" }
    },
    {
      "id": "prompt-need-more-info",
      "type": "prompt",
      "parentId": "group-3",
      "position": { "x": 300, "y": 250 },
      "data": { "label": "Need more info", "name": "prompt-need-more-info" }
    },
    {
      "id": "group-5",
      "type": "group",
      "position": { "x": 600, "y": 400 },
      "style": { "width": 550, "height": 450 },
      "data": { "label": "4. Analysis & Effort Estimation" }
    },
    {
      "id": "prompt-analysis-start",
      "type": "prompt",
      "parentId": "group-5",
      "position": { "x": 20, "y": 50 },
      "data": { "label": "Analyzing issue...", "name": "prompt-analysis-start" }
    },
    {
      "id": "agent-file-investigation",
      "type": "subAgent",
      "parentId": "group-5",
      "position": { "x": 20, "y": 140 },
      "data": { "label": "agent-file-investigation", "subagent_type": "explore" }
    },
    {
      "id": "agent-solution-design",
      "type": "subAgent",
      "parentId": "group-5",
      "position": { "x": 20, "y": 230 },
      "data": { "label": "agent-solution-design", "subagent_type": "plan" }
    },
    {
      "id": "prompt-estimate",
      "type": "prompt",
      "parentId": "group-5",
      "position": { "x": 20, "y": 320 },
      "data": { "label": "Effort Evaluation", "name": "prompt-estimate" }
    },
    {
      "id": "group-6-merged",
      "type": "group",
      "position": { "x": 1200, "y": 0 },
      "style": { "width": 550, "height": 550 },
      "data": { "label": "5. Code Fix & Verification" }
    },
    {
      "id": "ask-modify",
      "type": "askUserQuestion",
      "parentId": "group-6-merged",
      "position": { "x": 20, "y": 50 },
      "data": { "label": "Try the fix?", "name": "ask-modify" }
    },
    {
      "id": "agent-2",
      "type": "subAgent",
      "parentId": "group-6-merged",
      "position": { "x": 20, "y": 150 },
      "data": { "label": "agent-2 (Implement)", "subagent_type": "general-purpose" }
    },
    {
      "id": "prompt-1",
      "type": "prompt",
      "parentId": "group-6-merged",
      "position": { "x": 20, "y": 250 },
      "data": { "label": "Verification Steps", "name": "prompt-1" }
    },
    {
      "id": "ask-1",
      "type": "askUserQuestion",
      "parentId": "group-6-merged",
      "position": { "x": 20, "y": 350 },
      "data": { "label": "Verification Status?", "name": "ask-1" }
    },
    {
      "id": "agent-3",
      "type": "subAgent",
      "parentId": "group-6-merged",
      "position": { "x": 300, "y": 250 },
      "data": { "label": "agent-3 (Additional Fix)", "subagent_type": "general-purpose" }
    },
    {
      "id": "group-7",
      "type": "group",
      "position": { "x": 1200, "y": 600 },
      "style": { "width": 550, "height": 350 },
      "data": { "label": "6. Retrospective & Knowledge Persistence" }
    },
    {
      "id": "agent-retrospective",
      "type": "subAgent",
      "parentId": "group-7",
      "position": { "x": 20, "y": 50 },
      "data": { "label": "agent-retrospective", "subagent_type": "plan" }
    },
    {
      "id": "prompt-select",
      "type": "prompt",
      "parentId": "group-7",
      "position": { "x": 20, "y": 140 },
      "data": { "label": "Select proposals", "name": "prompt-select" }
    },
    {
      "id": "agent-reflect",
      "type": "subAgent",
      "parentId": "group-7",
      "position": { "x": 20, "y": 230 },
      "data": { "label": "agent-reflect", "subagent_type": "general-purpose" }
    },
    {
      "id": "start-1",
      "type": "start",
      "position": { "x": 240, "y": -100 },
      "data": { "label": "Start" }
    },
    {
      "id": "end_1",
      "type": "end",
      "position": { "x": 1450, "y": 1000 },
      "data": { "label": "End" }
    }
  ],
  "edges": [
    { "id": "e-start-ticket", "source": "start-1", "target": "prompt-ticket" },
    { "id": "e-ticket-fetch", "source": "prompt-ticket", "target": "prompt-gh-fetch" },
    { "id": "e-fetch-success", "source": "prompt-gh-fetch", "target": "prompt-understanding", "label": "Success" },
    { "id": "e-fetch-failure", "source": "prompt-gh-fetch", "target": "prompt-fetch-failed", "label": "Failure" },
    { "id": "e-failed-retry", "source": "prompt-fetch-failed", "target": "ask-retry-fetch" },
    { "id": "e-retry-yes", "source": "ask-retry-fetch", "target": "prompt-ticket", "label": "Yes, retry" },
    { "id": "e-retry-no", "source": "ask-retry-fetch", "target": "end_1", "label": "No, end workflow" },
    { "id": "e-und-ask", "source": "prompt-understanding", "target": "ask-understanding" },
    { "id": "e-ask-correct", "source": "ask-understanding", "target": "ask-reproduce", "label": "Correct, proceed" },
    { "id": "e-ask-needs-corr", "source": "ask-understanding", "target": "prompt-clarify", "label": "Needs correction" },
    { "id": "e-clarify-reproduce", "source": "prompt-clarify", "target": "ask-reproduce" },
    { "id": "e-repro-yes", "source": "ask-reproduce", "target": "prompt-reproduce", "label": "Yes, reproduce" },
    { "id": "e-repro-skip", "source": "ask-reproduce", "target": "prompt-analysis-start", "label": "Skip" },
    { "id": "e-repro-result", "source": "prompt-reproduce", "target": "ask-reproduce-result" },
    { "id": "e-res-reproduced", "source": "ask-reproduce-result", "target": "prompt-analysis-start", "label": "Reproduced" },
    { "id": "e-res-unable", "source": "ask-reproduce-result", "target": "prompt-analysis-start", "label": "Unable-proceed" },
    { "id": "e-res-more-info", "source": "ask-reproduce-result", "target": "prompt-need-more-info", "label": "Need-more-info" },
    { "id": "e-need-more-end", "source": "prompt-need-more-info", "target": "end_1" },
    { "id": "e-analysis-file", "source": "prompt-analysis-start", "target": "agent-file-investigation" },
    { "id": "e-file-design", "source": "agent-file-investigation", "target": "agent-solution-design" },
    { "id": "e-design-estimate", "source": "agent-solution-design", "target": "prompt-estimate" },
    { "id": "e-est-modify", "source": "prompt-estimate", "target": "ask-modify" },
    { "id": "e-mod-try", "source": "ask-modify", "target": "agent-2", "label": "Try the fix" },
    { "id": "e-mod-skip", "source": "ask-modify", "target": "agent-retrospective", "label": "Skip the fix" },
    { "id": "e-agent2-prompt1", "source": "agent-2", "target": "prompt-1" },
    { "id": "e-prompt1-ask1", "source": "prompt-1", "target": "ask-1" },
    { "id": "e-ask1-complete", "source": "ask-1", "target": "agent-retrospective", "label": "Verification complete" },
    { "id": "e-ask1-add", "source": "ask-1", "target": "agent-3", "label": "Additional fix needed" },
    { "id": "e-agent3-prompt1", "source": "agent-3", "target": "prompt-1" },
    { "id": "e-retro-select", "source": "agent-retrospective", "target": "prompt-select" },
    { "id": "e-select-reflect", "source": "prompt-select", "target": "agent-reflect" },
    { "id": "e-reflect-end", "source": "agent-reflect", "target": "end_1" }
  ]
}
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
