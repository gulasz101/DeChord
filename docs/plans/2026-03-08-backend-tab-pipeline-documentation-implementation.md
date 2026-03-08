# Backend Tab Pipeline Documentation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a backend-only README deep dive that documents the full tab-generation pipeline from stem acquisition to persisted tab artifacts.

**Architecture:** Extend the existing backend README section instead of creating a separate doc. The new section will map runtime entrypoints in `backend/app/main.py` to their downstream service modules and spell out the parameters, dependencies, artifacts, and extraction boundaries for future tool separation.

**Tech Stack:** Markdown, Mermaid, FastAPI backend modules, existing DeChord pipeline services.

---

**Execution Notes**
- TDD exception: this is a documentation-only task, so there is no behavior change to drive with failing tests.
- Subagent exception: subagent execution is required by repo policy, but this environment does not expose a subagent tool. The work will be completed directly with the limitation stated in commits and handoff.

### Task 1: Add approved plan artifacts

**Files:**
- Create: `docs/plans/2026-03-08-backend-tab-pipeline-doc-design.md`
- Create: `docs/plans/2026-03-08-backend-tab-pipeline-documentation-implementation.md`

- [x] Save the approved design in a dedicated plan file.
- [x] Save the implementation checklist in a dedicated plan file.
- [x] Commit the plan artifacts with the plan path in the message.

### Task 2: Document the backend tab-generation pipeline in README

**Files:**
- Modify: `README.md`
- Reference: `backend/app/main.py`
- Reference: `backend/app/stems.py`
- Reference: `backend/app/services/tab_pipeline.py`
- Reference: `backend/app/midi.py`
- Reference: `backend/app/tabs.py`

- [x] Add a dedicated `Backend Tab Generation Pipeline` section in the backend README area.
- [x] Document both backend entrypoints and their orchestration boundaries.
- [x] Add a Mermaid flowchart showing data flow, key parameters, and module dependencies.
- [x] Add parameter, dependency, artifact, and extraction-seam documentation.
- [x] Commit the README update with the plan path in the message.

### Task 3: Verify, reset, and hand off

**Files:**
- Modify: `docs/plans/2026-03-08-backend-tab-pipeline-documentation-implementation.md`

- [ ] Run a fresh README sanity check command.
- [ ] Run `make reset` before final verification handoff.
- [ ] Confirm the final diff matches the documented scope.
- [ ] Send the Telegram handoff summary via `ops/scripts/send-telegram-summary.sh`.
- [ ] Commit the final plan status update with the plan path in the message.
