# Stems Runtime + Player Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make stem splitting and playback work end-to-end with explicit full-mix/stems player modes, visible failure feedback, and fresh-state verification.

**Architecture:** Extend backend job status with explicit stem failure diagnostics and ensure stem dependencies are available at runtime. Refactor frontend upload/player flows so users can pick processing mode from all upload entry points and control playback mode (`Full Mix` vs `Stems`) with per-stem selection in a sidebar mixer. Preserve analysis success when stem splitting fails, but surface the warning to users.

**Tech Stack:** Python 3.13+, FastAPI, LibSQL, React 19, TypeScript, Bun/Vitest, Pytest

---

### Task 1: Create corrective remediation plan file

**Files:**
- Create: `docs/plans/2026-03-02-stems-runtime-player-remediation.md`

- [x] Step 1: Add implementation plan file with all tasks initially unchecked.
- [x] Step 2: Commit with message body referencing `docs/plans/2026-03-02-stems-runtime-player-remediation.md`.

### Task 2: Backend status contract for `stems_error` (TDD)

**Files:**
- Modify: `backend/tests/test_api.py`
- Modify: `backend/app/main.py`

- [x] Step 1: Add failing test asserting `/api/status/{job_id}` includes non-empty `stems_error` when stem splitting fails.
- [x] Step 2: Run targeted backend tests and confirm RED.
- [x] Step 3: Implement minimal backend changes to store and expose `stems_error`.
- [x] Step 4: Re-run targeted tests and confirm GREEN.
- [x] Step 5: Mark task done and commit with plan reference.

### Task 3: Backend stem runtime readiness + dependencies (TDD)

**Files:**
- Modify: `backend/tests/test_stems.py`
- Modify: `backend/app/stems.py`
- Modify: `backend/pyproject.toml`

- [x] Step 1: Add failing tests for dependency/runtime preflight diagnostics for stems.
- [x] Step 2: Run targeted backend tests and confirm RED.
- [x] Step 3: Implement preflight check and actionable error propagation for missing runtime modules.
- [x] Step 4: Add required runtime dependencies (including `lameenc`) to backend project dependencies.
- [x] Step 5: Re-run targeted tests and confirm GREEN.
- [x] Step 6: Mark task done and commit with plan reference.

### Task 4: Frontend upload mode selector parity in Song Library (TDD)

**Files:**
- Modify: `frontend/src/components/SongLibraryPanel.tsx`
- Modify: `frontend/src/components/__tests__/DropZoneUploadMode.test.tsx`
- Modify: `frontend/src/App.tsx`

- [x] Step 1: Add failing tests for mode selection availability in Song Library upload flow.
- [x] Step 2: Run targeted frontend tests and confirm RED.
- [x] Step 3: Implement mode selector + callback wiring to upload API path.
- [x] Step 4: Re-run targeted frontend tests and confirm GREEN.
- [x] Step 5: Mark task done and commit with plan reference.

### Task 5: Frontend player mode switch + sidebar mixer UX (TDD)

**Files:**
- Modify: `frontend/src/components/StemMixerPanel.tsx`
- Modify: `frontend/src/components/__tests__/StemMixerPanel.test.tsx`
- Modify: `frontend/src/App.tsx`

- [x] Step 1: Add failing tests for `Full Mix`/`Stems` mode controls and stem checkbox behavior.
- [x] Step 2: Run targeted frontend tests and confirm RED.
- [x] Step 3: Implement sidebar-style mixer panel with radio mode switch and stem checkboxes.
- [x] Step 4: Re-run targeted frontend tests and confirm GREEN.
- [x] Step 5: Mark task done and commit with plan reference.

### Task 6: Playback routing logic for mix/stems/fallback behavior (TDD)

**Files:**
- Modify: `frontend/src/lib/playbackSources.ts`
- Modify: `frontend/src/__tests__/App.integration.test.tsx`
- Create: `frontend/src/lib/__tests__/playbackSources.mode.test.ts`

- [ ] Step 1: Add failing tests for routing rules:
  - `Full Mix` -> mixed source only
  - `Stems` + selected stems -> stem sources only
  - `Stems` + no selected stems -> auto-fallback to full mix
- [ ] Step 2: Run targeted frontend tests and confirm RED.
- [ ] Step 3: Implement routing logic with explicit playback mode input.
- [ ] Step 4: Re-run targeted frontend tests and confirm GREEN.
- [ ] Step 5: Mark task done and commit with plan reference.

### Task 7: Visible frontend warning for stem split failure

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/__tests__/UploadWarning.integration.test.tsx`

- [ ] Step 1: Add failing test asserting warning visibility when `stems_status=failed` and `stems_error` is present.
- [ ] Step 2: Run targeted frontend tests and confirm RED.
- [ ] Step 3: Implement warning surface in upload/progress UX.
- [ ] Step 4: Re-run targeted frontend tests and confirm GREEN.
- [ ] Step 5: Mark task done and commit with plan reference.

### Task 8: Update AGENTS.md with mandatory post-development reset rule

**Files:**
- Modify: `AGENTS.md`

- [ ] Step 1: Add explicit rule requiring runtime reset after development and before final verification/handoff.
- [ ] Step 2: Mark task done and commit with plan reference.

### Task 9: Full verification gate

**Files:**
- No code changes expected

- [ ] Step 1: Run `cd backend && uv run pytest tests/ -v`.
- [ ] Step 2: Run `cd frontend && bun test`.
- [ ] Step 3: Run `cd frontend && bun run build`.
- [ ] Step 4: Mark task done and commit with plan reference if artifacts/documentation changes are made.

### Task 10: Fresh-state runtime reset gate

**Files:**
- No code changes expected

- [ ] Step 1: Run `make reset`.
- [ ] Step 2: Confirm backend runtime state is fresh (`backend/dechord.db` recreated on startup, empty song/stem data pre-upload).
- [ ] Step 3: Mark task done in plan.

### Task 11: MCP E2E verification with provided MP3

**Files:**
- No code changes expected

- [ ] Step 1: Start backend/frontend services.
- [ ] Step 2: Use MCP browser flow to upload `/Users/wojciechgula/Downloads/Clara Luciani - La grenade (Clip officiel) [85m-Qgo9_nE].mp3` with `Analyze + split stems`.
- [ ] Step 3: Verify completion payload shows successful stem split.
- [ ] Step 4: Verify DB has persisted rows in `song_stems` for uploaded song.
- [ ] Step 5: Verify sidebar player controls allow `Full Mix` vs `Stems`, and one/few/all stems playback behavior.
- [ ] Step 6: Mark task done in plan.
