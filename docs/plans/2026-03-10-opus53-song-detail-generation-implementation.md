# Opus 5-3 Song Detail Generation Implementation Plan

**Goal:** Design and implement real `Generate Stems` and `Generate Bass Tab` flows in the Opus 5-3 song detail page using the current backend pipelines and route architecture.

**Architecture:** Add song-scoped generation actions to the redesign detail flow, use explicit source selection for bass tab generation, and refresh the existing route state after generation completes.

**Tech Stack:** FastAPI, React 19, Vite, TypeScript, Vitest, pytest.

---

## Execution Checklist

- [x] Task 1: Confirm current backend pipeline reuse points for stem regeneration and bass-tab regeneration.
- [x] Task 2: Define the minimal backend API contracts for song-scoped generation.
- [ ] Task 3: Add backend tests for the new generation endpoints.
- [ ] Task 4: Implement backend generation endpoints and persistence updates.
- [ ] Task 5: Extend frontend API/types for generation flows and job/result handling.
- [ ] Task 6: Add Opus 5-3 song detail generation panels and source selection UX.
- [ ] Task 7: Wire `App.tsx` route refresh and progress handling for generation actions.
- [ ] Task 8: Verify flows end-to-end, run `make reset`, finalize plan state, and notify.

## Notes

- Use TDD for all implementation tasks.
- Reuse existing pipelines and persistence paths where possible.
- Do not ship dead controls: if one action cannot be completed in the same delivery, disable it honestly.
- Preserve Opus 5-3 design language.
- Current backend schema only stores one active `song_stems` row per `song_id + stem_key` and does not encode stem origin, uploader, archival state, or version lineage. This delivery should regenerate the current system set in place rather than introducing versioned asset history.
- Current backend already has reusable generation internals inside `backend/app/main.py`: `split_to_stems(...)`, `build_bass_analysis_stem(...)`, `tab_pipeline.run(...)`, `_persist_stems(...)`, `_persist_midi(...)`, and `_persist_tab(...)`.
- Current frontend `SongDetailPage` is a presentational component. Route refresh and API side effects currently live in `frontend/src/App.tsx`, so the new generation actions should follow that split instead of inventing a page-local data layer.

### Task 1: Confirm Backend Reuse Points

**Files to inspect:**
- `backend/app/main.py`
- `backend/app/db.py`
- `backend/app/db_schema.sql`
- stem, midi, and tab services used by upload flow

**Outcome:**
- Identify the exact callable path currently used for:
  - mix -> stems
  - bass stem -> midi
  - midi -> tab
- Decide whether the new routes can call those paths directly or need small extraction/refactoring.

**Audit result:**
- mix -> stems currently runs through `split_to_stems(...)` in `_run_analysis(...)`.
- bass/drums stems -> analysis bass stem -> midi/tab currently runs through `build_bass_analysis_stem(...)` plus `tab_pipeline.run(...)` in `_run_analysis(...)` and `/api/tab/from-demucs-stems`.
- persistence already exists via `_persist_stems(...)`, `_persist_midi(...)`, and `_persist_tab(...)`.
- Small extraction/refactoring is required so the new song-scoped routes can reuse this logic without duplicating the upload job implementation.

### Task 2: Define Backend API Contracts

**Recommended routes:**
- `POST /api/songs/{song_id}/stems/regenerate`
- `POST /api/songs/{song_id}/tabs/regenerate`

**Expected payloads:**
- stems regenerate: likely no body, operates on original song mix
- tab regenerate: body includes explicit source selection

**Expected responses:**
- Prefer a job-style response if generation is not near-instant
- Reuse existing polling model where practical

**Refined contract for current codebase:**
- `POST /api/songs/{song_id}/stems/regenerate`
  - no body
  - synchronous response for now: `{ "stems": [...] }`
  - reuses stored original mix from `songs.audio_blob`, writes refreshed `song_stems` rows
- `POST /api/songs/{song_id}/tabs/regenerate`
  - JSON body: `{ "source_stem_key": string }`
  - synchronous response for now: `{ "tab": {...} }`
  - validates that the requested song stem exists and that a `drums` stem exists for the rhythm grid pipeline
- Defer job polling integration for these routes. Existing polling is upload-job-specific and there is no shared job model for song-scoped actions yet.

### Task 3: Add Backend Tests First

**Tests to add:**
- stems regeneration endpoint returns success/job id and persists new system stems
- tab regeneration endpoint accepts source stem selection and persists new midi/tab assets
- failures return usable errors when source audio is missing or invalid

**Run before implementation:**
- targeted `pytest` for the new route tests only

### Task 4: Implement Backend Endpoints

**Implementation direction:**
- add route handlers in `backend/app/main.py`
- extract shared pipeline steps if the upload flow logic is too entangled
- persist source provenance for regenerated tab assets if current schema requires it

**Important guardrails:**
- current schema cannot distinguish manual vs system stems, so this delivery regenerates the current persisted stem set in place
- system stem regeneration should refresh the persisted generated asset set without changing unrelated song records
- tab generation must record which source was used

### Task 5: Extend Frontend API and Types

**Files:**
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`
- tests in `frontend/src/lib/__tests__/...`

**Add:**
- API helpers for song-scoped stems/tab regeneration
- request/response types
- any polling or status typing needed for the detail page

### Task 6: Implement 5-3 Generation Panels

**Primary file:**
- `frontend/src/redesign/pages/SongDetailPage.tsx`

**UX requirements:**
- `Generate Stems` opens a confirmation/progress panel
- `Generate Bass Tab` opens a source-selection/progress panel
- loading, success, and error states are visually explicit
- source selection is required or defaulted clearly for tab generation

**Tests first:**
- panel opening
- source selection rendering
- correct submit behavior
- loading/error/success states

### Task 7: Wire App Route Refresh

**Primary file:**
- `frontend/src/App.tsx`

**Responsibilities:**
- handle API calls from the redesign page
- poll if needed
- reload song detail after completion
- keep project/song route state coherent

**Integration tests:**
- route-level generation flow from song detail
- refreshed stems after stem regeneration
- refreshed tab availability after tab regeneration

### Task 8: Verify and Finalize

**Verification:**
- run backend targeted tests
- run frontend targeted tests
- run route integration tests
- run `make reset`

**Finish:**
- update all checklist items to `[x]`
- commit with the plan path in the message
- send Telegram summary unless explicitly skipped
