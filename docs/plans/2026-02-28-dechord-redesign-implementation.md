# DeChord Practice UX Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign DeChord into a polished, persistent localhost practice app with improved playback UX, notes/toasts, playback speed control, next-chord fretboard highlights, and LibSQL-backed song/audio persistence.

**Architecture:** Keep FastAPI + React monolith. Add LibSQL persistence and migrate backend APIs to song-centric reads while retaining analysis jobs. Frontend becomes library-driven with persistent playback preferences and note cue rendering.

**Tech Stack:** Python 3.13+, FastAPI, libsql-client, Bun, React 19, TypeScript, Tailwind v4, Vitest, Pytest

---

## Task 1: Add LibSQL dependency and DB module scaffolding

- [ ] Step 1: Write failing backend tests expecting DB module symbols
- [ ] Step 2: Run test to confirm fail
- [ ] Step 3: Add `libsql-client` dependency and create DB module files
- [ ] Step 4: Re-run tests to pass
- [ ] Step 5: Commit

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/app/db.py`
- Create: `backend/app/models.py`
- Create: `backend/tests/test_db_bootstrap.py`

## Task 2: Create schema + bootstrap + default user (`Wojtek`)

- [ ] Step 1: Write failing tests for table creation/default user
- [ ] Step 2: Run fail
- [ ] Step 3: Implement migration/bootstrap SQL in backend startup utilities
- [ ] Step 4: Run tests pass
- [ ] Step 5: Commit

**Files:**
- Modify: `backend/app/db.py`
- Create: `backend/app/db_schema.sql`
- Modify: `backend/tests/test_db_bootstrap.py`

## Task 3: Persist songs/audio blobs and analysis records

- [ ] Step 1: Write failing API tests for persisted song lifecycle
- [ ] Step 2: Run fail
- [ ] Step 3: Implement repository operations and wire `/api/analyze`, `/api/result/{job_id}`
- [ ] Step 4: Run API tests pass
- [ ] Step 5: Commit

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/models.py`
- Modify: `backend/tests/test_api.py`

## Task 4: Add song library endpoints and audio-by-song streaming

- [ ] Step 1: Write failing tests for `GET /api/songs`, `GET /api/songs/{id}`, `GET /api/audio/{song_id}`
- [ ] Step 2: Run fail
- [ ] Step 3: Implement endpoints + serializers
- [ ] Step 4: Run tests pass
- [ ] Step 5: Commit

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

## Task 5: Add notes CRUD + playback preferences APIs

- [ ] Step 1: Write failing tests for note creation/update/delete and prefs save/load
- [ ] Step 2: Run fail
- [ ] Step 3: Implement endpoints and DB logic
- [ ] Step 4: Run tests pass
- [ ] Step 5: Commit

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/models.py`
- Modify: `backend/tests/test_api.py`

## Task 6: Frontend API/types expansion for songs, notes, prefs

- [ ] Step 1: Write failing frontend type/API tests
- [ ] Step 2: Run fail
- [ ] Step 3: Implement API client and types for library/note/prefs flows
- [ ] Step 4: Run tests pass
- [ ] Step 5: Commit

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/__tests__/api.contract.test.ts`

## Task 7: Build Song Library panel and persisted song selection

- [ ] Step 1: Write failing UI test for library rendering/selection
- [ ] Step 2: Run fail
- [ ] Step 3: Implement `SongLibraryPanel` and integrate into App layout
- [ ] Step 4: Run tests pass
- [ ] Step 5: Commit

**Files:**
- Create: `frontend/src/components/SongLibraryPanel.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/__tests__/SongLibraryPanel.test.tsx`

## Task 8: Playback speed control (40%-200%) persisted per song

- [ ] Step 1: Write failing tests for speed selector and audio rate updates
- [ ] Step 2: Run fail
- [ ] Step 3: Add speed state to player hook + transport dropdown + persistence calls
- [ ] Step 4: Run tests pass
- [ ] Step 5: Commit

**Files:**
- Modify: `frontend/src/hooks/useAudioPlayer.ts`
- Modify: `frontend/src/components/TransportBar.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/__tests__/PlaybackSpeed.test.tsx`

## Task 9: Fretboard next-chord highlighting

- [ ] Step 1: Write failing tests for current vs next note rendering state
- [ ] Step 2: Run fail
- [ ] Step 3: Extend fretboard props/rendering with dual-highlight logic
- [ ] Step 4: Run tests pass
- [ ] Step 5: Commit

**Files:**
- Modify: `frontend/src/components/Fretboard.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/__tests__/FretboardHighlights.test.tsx`

## Task 10: Note creation UX (timestamp + chord modal flows)

- [ ] Step 1: Write failing tests for modal open/save behavior
- [ ] Step 2: Run fail
- [ ] Step 3: Implement note modal and event wiring from progress/chord interactions
- [ ] Step 4: Run tests pass
- [ ] Step 5: Commit

**Files:**
- Create: `frontend/src/components/NoteEditorModal.tsx`
- Modify: `frontend/src/components/ChordTimeline.tsx`
- Modify: `frontend/src/components/TransportBar.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/__tests__/NoteEditorModal.test.tsx`

## Task 11: Toast cue system + note markers on progress/timeline

- [ ] Step 1: Write failing tests for note marker and toast trigger timing
- [ ] Step 2: Run fail
- [ ] Step 3: Implement toast scheduler, marker rendering, and overlap handling
- [ ] Step 4: Run tests pass
- [ ] Step 5: Commit

**Files:**
- Create: `frontend/src/components/ToastCueLayer.tsx`
- Modify: `frontend/src/components/ChordTimeline.tsx`
- Modify: `frontend/src/components/TransportBar.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/lib/toastScheduler.ts`
- Create: `frontend/src/lib/__tests__/toastScheduler.test.ts`

## Task 12: Visual polish pass (Guitar Pro / GoPlayAlong-inspired playback UX)

- [ ] Step 1: Write failing snapshot/assertion tests for key visual states
- [ ] Step 2: Run fail
- [ ] Step 3: Apply Tailwind/layout refinements and consistent visual hierarchy
- [ ] Step 4: Run tests/build pass
- [ ] Step 5: Commit

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/components/Header.tsx`
- Modify: `frontend/src/components/ChordTimeline.tsx`
- Modify: `frontend/src/components/Fretboard.tsx`
- Modify: `frontend/src/components/TransportBar.tsx`
- Modify: `frontend/src/App.tsx`

## Task 13: End-to-end verification and docs update

- [ ] Step 1: Run backend tests
- [ ] Step 2: Run frontend tests
- [ ] Step 3: Run frontend build
- [ ] Step 4: Update README usage for library/notes/speed/tmux flow
- [ ] Step 5: Commit

**Files:**
- Modify: `README.md`

---

## Verification Commands

```bash
cd backend && uv run pytest tests/ -v
cd frontend && bun test
cd frontend && bun run build
```

## Process Notes

- TDD: required for each task (RED -> GREEN -> REFACTOR).
- Subagent-driven-development: followed in subagent-style phases due runtime limitation (no native subagent dispatch primitive).
- Commit message format:

```text
Task N: <description>

refs: docs/plans/2026-02-28-dechord-redesign-implementation.md
```
