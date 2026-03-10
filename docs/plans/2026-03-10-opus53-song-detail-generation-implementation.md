# Opus 5-3 Song Detail Generation Implementation Plan

**Goal:** Design and implement real `Generate Stems` and `Generate Bass Tab` flows in the Opus 5-3 song detail page using the current backend pipelines and route architecture.

**Architecture:** Add song-scoped generation actions to the redesign detail flow, use explicit source selection for bass tab generation, and refresh the existing route state after generation completes.

**Tech Stack:** FastAPI, React 19, Vite, TypeScript, Vitest, pytest.

---

## Execution Checklist

- [ ] Task 1: Confirm current backend pipeline reuse points for stem regeneration and bass-tab regeneration.
- [ ] Task 2: Define the minimal backend API contracts for song-scoped generation.
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
- manual stems must not be deleted by stem regeneration
- system stem regeneration should refresh only the system-generated asset set
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
