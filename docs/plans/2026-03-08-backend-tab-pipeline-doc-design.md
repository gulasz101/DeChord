# Backend Tab Pipeline Documentation Design

> **Status Tracking**
- [x] Confirm scope is the web backend tab-generation pipeline only.
- [x] Choose the README as the canonical documentation location.
- [x] Approve the documentation structure before implementation.

**Goal:** Document the backend web-app tab generation pipeline in the root README with enough detail to support future extraction into a standalone tabs tool.

**Scope:** Cover only the FastAPI backend path that turns a source mix or uploaded stems into persisted AlphaTex tabs and related diagnostics. Explicitly exclude the legacy desktop app.

**Documentation shape:**
- Add one dedicated README section focused on the backend tab-generation pipeline.
- Explain the two backend entrypoints:
  - async upload-job flow in `backend/app/main.py`
  - direct `POST /api/tab/from-demucs-stems` flow
- Describe each stage in order:
  - source audio or uploaded stems
  - stem separation
  - analysis-stem refinement and candidate selection
  - bass transcription and note recovery paths
  - drum-derived rhythm extraction and bar grid building
  - cleanup, quantization, fingering, AlphaTex export
  - persistence and retrieval endpoints
- Include one Mermaid flowchart with stage inputs, outputs, parameters, and module dependencies called out inline.
- Include compact tables/lists for:
  - route-level request parameters
  - `TabPipeline.run(...)` parameters
  - environment-variable dependency groups
  - persisted artifacts and runtime outputs
  - likely extraction seams for a future standalone service

**Constraints and method notes:**
- This is a documentation-only change. TDD is not meaningfully applicable because no production behavior changes are being introduced.
- Subagent-driven development is not available in this environment, so the work will be executed directly in the current session.
