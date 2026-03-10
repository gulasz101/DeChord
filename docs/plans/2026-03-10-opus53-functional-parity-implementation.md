# Opus 5-3 Functional Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restore pre-refactor MVP functionality behind the Opus 5-3 redesign surfaces and add song-scoped manual stem upload.

**Architecture:** Keep the current route-driven Opus 5-3 pages, replace presentation-only logic with the real upload/player/detail workflows from the MVP, and add a single backend/API flow for manual stem upload within a song.

**Tech Stack:** FastAPI, React 19, Vite, TypeScript, Vitest, pytest.

---

## Execution Checklist

- [x] Task 1: Add backend song-scoped stem upload API and persistence.
- [x] Task 2: Extend frontend API/types for manual stem upload.
- [x] Task 3: Restore song upload flow in `SongLibraryPage` with progress and warnings.
- [x] Task 4: Add Opus 5-3 stem upload UI in `SongDetailPage`.
- [x] Task 5: Restore real player functionality behind `PlayerPage`.
- [x] Task 6: Wire redesigned routes through `App.tsx` and refresh flows.
- [x] Task 7: Verify, reset, finalize plan status, and notify.
- [x] Task 8: Re-run verification/reset after the player parity follow-up.

## Implementation Notes

- Subagent-driven development cannot be applied in this environment because no subagent/task-dispatch tool is available. Execute directly in-session while preserving the plan/task discipline.
- TDD still applies to every behavior change.
- Commit after each completed task with a message referencing this plan path.

### Task 1: Add Backend Song-Scoped Stem Upload API And Persistence

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

**Step 1: Write the failing test**
- Add a backend API test that uploads a stem file to an existing song via `POST /api/songs/{song_id}/stems`.
- Assert `200`, stored metadata, and visibility through `GET /api/songs/{song_id}/stems`.

**Step 2: Run the targeted test and verify it fails**
- Run: `cd backend && uv run pytest tests/test_api.py -k song_scoped_stem_upload -v`

**Step 3: Implement the minimal backend route**
- Save uploaded file under the existing stems area for the song.
- Persist metadata in `song_stems`.
- Return created stem payload or success response.

**Step 4: Run targeted backend tests and verify they pass**
- Run: `cd backend && uv run pytest tests/test_api.py -k "song_scoped_stem_upload or stems" -v`

**Step 5: Commit**
- `git commit -m "feat: add song-scoped manual stem upload API (docs/plans/2026-03-10-opus53-functional-parity-implementation.md)"`

### Task 2: Extend Frontend API/Types For Manual Stem Upload

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/types.ts`
- Add/Modify tests in: `frontend/src/lib/__tests__/api.stems-status.test.ts`

**Step 1: Write the failing test**
- Add a frontend API test asserting multipart body for manual stem upload and response parsing.

**Step 2: Run targeted test and verify it fails**
- Run: `cd frontend && npm test -- api.stems-status.test.ts`

**Step 3: Implement minimal API client/types**
- Add upload helper for manual stem uploads.
- Add any new response/type definitions required by the redesign pages.

**Step 4: Re-run targeted tests**
- Run: `cd frontend && npm test -- api.stems-status.test.ts`

**Step 5: Commit**
- `git commit -m "feat: add frontend manual stem upload client (docs/plans/2026-03-10-opus53-functional-parity-implementation.md)"`

### Task 3: Restore Song Upload Flow In `SongLibraryPage`

**Files:**
- Modify: `frontend/src/redesign/pages/SongLibraryPage.tsx`
- Add tests: `frontend/src/redesign/pages/__tests__/SongLibraryPage.test.tsx`
- Modify integration tests as needed: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Write failing frontend tests**
- Test upload toggle, file selection, process mode/quality capture, progress/error/warning rendering, and submit handler calls.

**Step 2: Run targeted tests and verify they fail**
- Run: `cd frontend && npm test -- SongLibraryPage.test.tsx App.integration.test.tsx`

**Step 3: Implement minimal UI wiring**
- Add real file input and drag/drop support.
- Surface upload status and warnings in the Opus 5-3 card.
- Keep styling aligned with 5-3.

**Step 4: Re-run targeted tests**
- Run: `cd frontend && npm test -- SongLibraryPage.test.tsx App.integration.test.tsx`

**Step 5: Commit**
- `git commit -m "feat: restore opus 5-3 song upload flow (docs/plans/2026-03-10-opus53-functional-parity-implementation.md)"`

### Task 4: Add Opus 5-3 Stem Upload UI In `SongDetailPage`

**Files:**
- Modify: `frontend/src/redesign/pages/SongDetailPage.tsx`
- Modify/Add tests: `frontend/src/redesign/pages/__tests__/SongDetailPage.test.tsx`

**Step 1: Write failing tests**
- Cover opening the upload panel, entering file/name/description, submitting, and showing loading or error state.

**Step 2: Run targeted tests and verify they fail**
- Run: `cd frontend && npm test -- SongDetailPage.test.tsx`

**Step 3: Implement minimal UI flow**
- Add inline upload panel in the song detail page.
- Keep the visual language consistent with existing 5-3 panels.

**Step 4: Re-run targeted tests**
- Run: `cd frontend && npm test -- SongDetailPage.test.tsx`

**Step 5: Commit**
- `git commit -m "feat: add opus 5-3 manual stem upload flow (docs/plans/2026-03-10-opus53-functional-parity-implementation.md)"`

### Task 5: Restore Real Player Functionality Behind `PlayerPage`

**Files:**
- Modify: `frontend/src/redesign/pages/PlayerPage.tsx`
- Reuse/modify: `frontend/src/hooks/useAudioPlayer.ts`
- Reuse/modify: `frontend/src/lib/playbackSources.ts`
- Add/modify tests around player behavior

**Step 1: Write failing tests**
- Cover real tab source selection, real stem/full mix playback mode decisions, and note interaction wiring where practical.

**Step 2: Run targeted tests and verify they fail**
- Run: `cd frontend && npm test -- App.integration.test.tsx useAudioPlayerStems.test.ts TabViewerPanel.test.tsx`

**Step 3: Implement minimal real-player wiring**
- Replace simulated timer playback with real audio player hook.
- Use real tab URLs and real stem playback sources.
- Restore playback prefs persistence and note interactions through parent props.

**Step 4: Re-run targeted tests**
- Run: `cd frontend && npm test -- App.integration.test.tsx useAudioPlayerStems.test.ts TabViewerPanel.test.tsx`

**Step 5: Commit**
- `git commit -m "feat: restore opus 5-3 player functional parity (docs/plans/2026-03-10-opus53-functional-parity-implementation.md)"`

### Task 6: Wire Redesigned Routes Through `App.tsx` And Refresh Flows

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify integration tests: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Write failing integration tests**
- Cover route-level upload completion, song detail refresh after stem upload, and player route using refreshed song data.

**Step 2: Run targeted tests and verify they fail**
- Run: `cd frontend && npm test -- App.integration.test.tsx`

**Step 3: Implement minimal orchestration changes**
- Pass real handlers into redesign pages.
- Refresh project songs and song detail state after uploads.
- Keep route transitions stable.

**Step 4: Re-run targeted tests**
- Run: `cd frontend && npm test -- App.integration.test.tsx`

**Step 5: Commit**
- `git commit -m "feat: wire opus 5-3 routes to restored workflows (docs/plans/2026-03-10-opus53-functional-parity-implementation.md)"`

### Task 7: Verify, Reset, Finalize Plan Status, And Notify

**Files:**
- Modify: `docs/plans/2026-03-10-opus53-functional-parity-implementation.md`

**Step 1: Run verification**
- Run targeted backend and frontend tests used during implementation.
- Run broader checks if feasible.

**Step 2: Run reset workflow**
- Run: `make reset`

**Step 3: Mark completed checklist items**
- Update all completed tasks from `[ ]` to `[x]` in this plan.

**Step 4: Commit final verification state**
- `git commit -m "test: verify opus 5-3 functional parity restoration (docs/plans/2026-03-10-opus53-functional-parity-implementation.md)"`
