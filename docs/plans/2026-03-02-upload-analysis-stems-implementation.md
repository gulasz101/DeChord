# Upload Analysis/Stems Modes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add upload mode selection (analysis-only vs analysis+stems), real stage-based progress reporting, and stem-aware playback controls with per-stem muting.

**Architecture:** Extend existing analyze job to a staged pipeline with structured progress payload. Add Demucs-backed stem separation service and persistence. Frontend adds upload mode selection, stage progress visualization, and synchronized multi-audio stem playback with checkbox toggles.

**Tech Stack:** Python 3.13+, FastAPI, madmom, demucs, FFmpeg, React 19, TypeScript, Vitest, Pytest

---

### Task 0: Fix frontend test runner baseline (blocker)

**Files:**
- Modify: `Makefile`
- Modify: `README.md`

- [x] Step 1: Reproduce frontend failure with `cd frontend && bun test` and capture error.
- [x] Step 2: Verify `cd frontend && bun run test` passes to confirm runner mismatch root cause.
- [x] Step 3: Replace project references from `bun test` to `bun run test` in actionable docs/scripts.
- [x] Step 4: Re-run `cd frontend && bun run test` and `make test` to verify the runner path is stable.
- [x] Step 5: Commit with plan reference.

### Task 1: Backend contracts for staged job status and process mode

**Files:**
- Modify: `backend/tests/test_api.py`
- Modify: `backend/app/models.py`

- [x] Step 1: Write failing backend tests for `POST /api/analyze` accepting `process_mode` (`analysis_only`, `analysis_and_stems`).
- [x] Step 2: Write failing tests asserting `/api/status/{job_id}` returns `stage`, `progress_pct`, `stage_progress_pct`, and `message`.
- [x] Step 3: Run `cd backend && uv run pytest tests/test_api.py -v` and confirm failures.
- [x] Step 4: Add/adjust request and response models minimally to satisfy schema.
- [x] Step 5: Re-run tests and ensure these contract tests pass.
- [x] Step 6: Commit with message referencing `docs/plans/2026-03-02-upload-analysis-stems-implementation.md`.

### Task 2: DB schema for stems metadata

**Files:**
- Modify: `backend/app/db_schema.sql`
- Modify: `backend/tests/test_db_bootstrap.py`

- [x] Step 1: Write failing DB bootstrap test for new `song_stems` table and required indexes.
- [x] Step 2: Run `cd backend && uv run pytest tests/test_db_bootstrap.py -v` and confirm failure.
- [x] Step 3: Add `song_stems` schema (`song_id`, `stem_key`, `relative_path`, `mime_type`, `duration`, timestamps).
- [x] Step 4: Re-run DB bootstrap test and confirm pass.
- [x] Step 5: Commit with plan reference in commit body.

### Task 3: Create stem separation service (Demucs-based)

**Files:**
- Create: `backend/app/stems.py`
- Create: `backend/tests/test_stems.py`
- Modify: `backend/pyproject.toml`

- [x] Step 1: Write failing unit tests for `split_to_stems(audio_path, on_progress)` contract with mocked Demucs adapter.
- [x] Step 2: Run `cd backend && uv run pytest tests/test_stems.py -v` and confirm fail.
- [x] Step 3: Add minimal `stems.py` service with Demucs wrapper and callback-based progress events.
- [x] Step 4: Add backend dependency entries needed for Demucs integration.
- [x] Step 5: Re-run targeted tests and confirm pass.
- [x] Step 6: Commit with plan reference.

### Task 4: Implement staged progress engine in analyze job runner

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

- [x] Step 1: Add failing API tests asserting stage transitions for `analysis_only` and `analysis_and_stems`.
- [x] Step 2: Run `cd backend && uv run pytest tests/test_api.py -v` and confirm fail.
- [x] Step 3: Refactor `_run_analysis` into stage helpers updating `progress_pct` and `stage_progress_pct`.
- [x] Step 4: Wire stem stage to call `split_to_stems` only when requested.
- [x] Step 5: Ensure partial success behavior: analysis success + stems failure still returns analysis.
- [x] Step 6: Re-run tests and confirm pass.
- [x] Step 7: Commit with plan reference.

### Task 5: Persist and expose stems via API

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

- [x] Step 1: Write failing tests for `GET /api/songs/{song_id}/stems` and stream endpoint `GET /api/audio/{song_id}/stems/{stem_key}`.
- [x] Step 2: Run targeted tests and confirm fail.
- [x] Step 3: Implement metadata persistence and both endpoints.
- [x] Step 4: Re-run tests and confirm pass.
- [x] Step 5: Commit with plan reference.

### Task 6: Frontend API/type expansion for upload mode and staged status

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/__tests__/api.stems-status.test.ts`

- [x] Step 1: Write failing frontend tests for upload call including `process_mode` and status shape parsing.
- [x] Step 2: Run `cd frontend && bun test frontend/src/lib/__tests__/api.stems-status.test.ts` (or project test command) and confirm fail.
- [x] Step 3: Update API client/types for staged status and stem list fetch.
- [x] Step 4: Re-run tests and confirm pass.
- [x] Step 5: Commit with plan reference.

### Task 7: Upload mode selection UI

**Files:**
- Modify: `frontend/src/components/DropZone.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/__tests__/DropZoneUploadMode.test.tsx`

- [x] Step 1: Write failing UI tests for mode selector with two options and correct callback payload.
- [x] Step 2: Run targeted frontend tests and confirm fail.
- [x] Step 3: Implement mode selector and pass selected mode into `uploadAudio`.
- [x] Step 4: Re-run tests and confirm pass.
- [x] Step 5: Commit with plan reference.

### Task 8: Real progress visualization in upload UI

**Files:**
- Modify: `frontend/src/components/DropZone.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/__tests__/UploadProgressStages.test.tsx`

- [ ] Step 1: Write failing tests for overall progress bar and stage text rendering.
- [ ] Step 2: Run targeted tests and confirm fail.
- [ ] Step 3: Implement progress bar UI bound to `progress_pct` and `stage_progress_pct`.
- [ ] Step 4: Re-run tests and confirm pass.
- [ ] Step 5: Commit with plan reference.

### Task 9: Multi-stem playback hook support

**Files:**
- Modify: `frontend/src/hooks/useAudioPlayer.ts`
- Create: `frontend/src/hooks/__tests__/useAudioPlayerStems.test.ts`

- [ ] Step 1: Write failing hook tests for synchronized play/pause/seek/rate across multiple audio elements.
- [ ] Step 2: Run targeted tests and confirm fail.
- [ ] Step 3: Refactor hook to support either single source or multiple stem sources.
- [ ] Step 4: Re-run tests and confirm pass.
- [ ] Step 5: Commit with plan reference.

### Task 10: Stem mixer UI (checkbox mute controls)

**Files:**
- Create: `frontend/src/components/StemMixerPanel.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/__tests__/StemMixerPanel.test.tsx`

- [ ] Step 1: Write failing tests for rendering detected stems and default all-checked state.
- [ ] Step 2: Run targeted tests and confirm fail.
- [ ] Step 3: Implement mixer panel with checkbox toggles and integrate with player state.
- [ ] Step 4: Re-run tests and confirm pass.
- [ ] Step 5: Commit with plan reference.

### Task 11: Fallback behavior and mixed-track compatibility

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/__tests__/App.integration.test.tsx`

- [ ] Step 1: Write failing integration tests for songs with no stems (single-track fallback).
- [ ] Step 2: Write failing integration tests for songs with stems (mixer visible + stems used).
- [ ] Step 3: Run integration tests and confirm fail.
- [ ] Step 4: Implement fallback routing logic and conditional UI.
- [ ] Step 5: Re-run integration tests and confirm pass.
- [ ] Step 6: Commit with plan reference.

### Task 12: Backend and frontend full verification

**Files:**
- Modify: `README.md`

- [ ] Step 1: Run `cd backend && uv run pytest tests/ -v`.
- [ ] Step 2: Run `cd frontend && bun test`.
- [ ] Step 3: Run `cd frontend && bun run build`.
- [ ] Step 4: Update README upload/stem workflow documentation and troubleshooting notes.
- [ ] Step 5: Re-run affected tests after docs/code touch if needed.
- [ ] Step 6: Commit with plan reference.

---

## Verification Commands

```bash
cd backend && uv run pytest tests/ -v
cd frontend && bun test
cd frontend && bun run build
```

## Execution Workflow (Required)

- `using-superpowers`
- `brainstorming`
- `writing-plans`
- `executing-plans`

## Process Guardrails

- TDD is mandatory in every implementation task: RED -> GREEN -> REFACTOR.
- Subagent-driven-development is mandatory during execution (fresh subagent per independent task where available).
- Every task completion must update this plan file from `[ ]` to `[x]`.
- Every task completion must produce a commit referencing this plan file path.
