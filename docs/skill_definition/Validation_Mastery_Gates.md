# NamoNexus Validation & Mastery Gates

This document defines the testing and quality assurance standards to ensure the project's success.

## 1. Mastery Gates (Automated Tests)
Every critical feature must pass a "Mastery Gate" before deployment:
- **Search Accuracy Gate**: Top RAG result must match expected keywords (e.g., "Four Noble Truths" search must return "Dhammacakkappavattana Sutta").
- **Performance Gate**: WebSocket response latency must be < 500ms for metadata updates.
- **Safety Gate**: Zero tolerance for hallucinating "fake" Dhamma quotes.

## 2. Quality Metrics (KPIs)
- **Vector Coverage**: All 168k vectors must be reachable and indexed correctly.
- **Sentiment Alignment**: AI response tone must match the detected student emotion with > 85% accuracy.
- **Type Integrity**: 0 TypeScript errors in `frontend/src`; 100% test coverage for `namo_core/services`.

## 3. Manual Verification Checklist
- [ ] **Visual WOW**: Does the UI feel "premium" and "sovereign"?
- [ ] **Persona Check**: Is the response blunt, direct, and witty? Does it address P'Ice?
- [ ] **Tablet Flow**: Is the touch interface responsive on 10.5" tablets?
- [ ] **Secret Hygiene**: Are there any hardcoded keys in the PR?

## 4. Success Definition
Success is achieved when the NamoNexus Smart Classroom can:
1. Automatically detect student disengagement.
2. Provide a teaching hint to the teacher.
3. Generate a scripturally accurate Dhamma explanation that restores engagement.
4. Document the entire process for the teacher's notebook.
