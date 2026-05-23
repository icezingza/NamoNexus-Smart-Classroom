# Development Analysis

## Current State

The recovered project now has a working end-to-end demo path:

- FastAPI backend with health, status, knowledge, lessons, devices, and reasoning routes
- React dashboard with live calls to backend endpoints
- A basic AI chat screen wired to the rebuilt reasoning chat route
- Local backup automation for the reconstructed workspace
- Backend `pytest` and frontend `vitest`/`vite build` pass on the recovered baseline

## Strengths

- The package and folder layout now resembles the earlier observed architecture.
- Knowledge, lessons, devices, and reasoning are separated into service layers.
- The frontend can exercise real backend flows instead of placeholders only.
- The project can be tested and built locally with simple commands.

## Main Gaps

1. The reasoning layer has a provider adapter plus runtime fallback to mock, but the practical default path is still mock/demo unless provider config is supplied.
2. The knowledge search uses a small local corpus with `tf-idf-lite`, not embeddings or vector retrieval.
3. Device, speech, vision, and empathy flows are simulated or probe-only and do not yet run a real classroom control loop.
4. The dashboard still uses simple request/response flows; there is no authentication, streaming, or user/session model.
5. The original source and git history are still unrecovered.

## Recommended Next Build Order

1. Put a real LLM provider behind `services/reasoning/providers` in the target environment and validate it with real credentials and endpoint behavior.
2. Upgrade `services/knowledge` from `tf-idf-lite` and sample files to embeddings plus indexed retrieval over real curriculum content.
3. Expand classroom/device control behind feature flags so the mocked flows remain usable while real adapters are introduced.
4. Add TTS/output delivery and close the loop between reasoning responses and classroom outputs.
5. Grow API contract tests and frontend interaction tests around reasoning, devices, and classroom state as interfaces stabilize.

## Practical Rule

Treat the current codebase as a clean recovery baseline, not as a faithful copy of the lost source.
New work should be layered onto this structure deliberately instead of trying to infer missing code blindly.
