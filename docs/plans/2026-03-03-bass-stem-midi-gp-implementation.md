# Bass Stem MIDI + Guitar Pro Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an end-to-end EADG-only pipeline that generates bass MIDI from the persisted bass stem, converts MIDI to GP5 tabs, and renders synced tabs with existing playback/chords.

**Architecture:** Extend the current staged backend job pipeline with two new artifact stages (`transcribing_bass_midi`, `generating_tabs`) and persist binary outputs in LibSQL BLOB tables (`song_midis`, `song_tabs`). Add a transcription adapter layer (`basic-pitch` first), an EADG tab mapper + GP5 exporter, and frontend tab rendering via alphaTab synchronized to the existing audio player master clock.

**Tech Stack:** Python 3.13+, FastAPI, LibSQL, Pytest, basic-pitch, PyGuitarPro, React 19, TypeScript, Vitest, alphaTab

---

### Task 1: Schema + DB bootstrap for MIDI/Tabs artifacts (TDD)

**Files:**
- Modify: `backend/app/db_schema.sql`
- Modify: `backend/tests/test_db_bootstrap.py`

- [ ] **Step 1: Write failing DB test for new tables and constraints**
  - Add assertions for existence of `song_midis` and `song_tabs` with required columns and indexes.
  - Include constraints:
    - unique latest per source (`UNIQUE(song_id, source_stem_key)` for midi)
    - `FOREIGN KEY(source_midi_id) REFERENCES song_midis(id) ON DELETE CASCADE`

- [ ] **Step 2: Run RED test**
  - Run: `cd backend && uv run pytest tests/test_db_bootstrap.py -q`
  - Expected: `FAIL` because tables do not yet exist.

- [ ] **Step 3: Implement schema changes**
  - Add table definitions and indexes in `backend/app/db_schema.sql`.

- [ ] **Step 4: Run GREEN test**
  - Run: `cd backend && uv run pytest tests/test_db_bootstrap.py -q`
  - Expected: `PASS`.

- [ ] **Step 5: Commit**
  - Run:
  ```bash
  git add backend/app/db_schema.sql backend/tests/test_db_bootstrap.py
  git commit -m "feat(db): add song_midis and song_tabs schema" -m "Refs: docs/plans/2026-03-03-bass-stem-midi-gp-implementation.md"
  ```

### Task 2: Bass stem -> MIDI service contract and basic-pitch adapter (TDD)

**Files:**
- Create: `backend/app/midi.py`
- Create: `backend/tests/test_midi.py`
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Write failing tests for transcription contract**
  - Add tests for:
    - successful generation returns non-empty MIDI bytes
    - missing bass stem path raises descriptive runtime error
    - engine failure maps to controlled error message
  - Example test core:
  ```python
  def test_transcribe_bass_stem_returns_midi_bytes(tmp_path):
      stem = tmp_path / "bass.wav"
      stem.write_bytes(b"fake")
      midi = midi_service.transcribe_bass_stem_to_midi(stem, transcribe_fn=lambda *_: b"MThd...")
      assert midi.startswith(b"MThd")
  ```

- [ ] **Step 2: Run RED test**
  - Run: `cd backend && uv run pytest tests/test_midi.py -q`
  - Expected: `FAIL` (`ModuleNotFoundError` / missing implementation).

- [ ] **Step 3: Implement minimal service + adapter**
  - `midi.py`:
    - `transcribe_bass_stem_to_midi(input_wav: Path, transcribe_fn: ... | None = None) -> bytes`
    - default engine path uses `basic-pitch` (wrapper function) and writes temporary midi file, returns bytes.

- [ ] **Step 4: Add dependency**
  - Add `basic-pitch` in backend dependencies and lockfile update via `uv sync`.

- [ ] **Step 5: Run GREEN tests**
  - Run: `cd backend && uv run pytest tests/test_midi.py -q`
  - Expected: `PASS`.

- [ ] **Step 6: Commit**
  - Run:
  ```bash
  git add backend/app/midi.py backend/tests/test_midi.py backend/pyproject.toml backend/uv.lock
  git commit -m "feat(backend): add bass stem to midi transcription service" -m "Refs: docs/plans/2026-03-03-bass-stem-midi-gp-implementation.md"
  ```

### Task 3: Job pipeline integration + MIDI persistence/status (TDD)

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing API tests for new stage/status**
  - Assertions:
    - `stage` transitions include `transcribing_bass_midi`
    - status payload includes `midi_status` and `midi_error`
    - successful jobs persist latest midi artifact for song.

- [ ] **Step 2: Run RED test**
  - Run: `cd backend && uv run pytest tests/test_api.py -q`
  - Expected: `FAIL` on missing stage/fields.

- [ ] **Step 3: Implement minimal pipeline changes**
  - Integrate `transcribe_bass_stem_to_midi` after stems stage.
  - Add `_persist_midi(song_id, midi_bytes, ...)`.
  - Preserve partial success (analysis/stems remain complete even if midi fails).

- [ ] **Step 4: Run GREEN test**
  - Run: `cd backend && uv run pytest tests/test_api.py -q`
  - Expected: `PASS`.

- [ ] **Step 5: Commit**
  - Run:
  ```bash
  git add backend/app/main.py backend/tests/test_api.py
  git commit -m "feat(api): add bass midi stage and status contract" -m "Refs: docs/plans/2026-03-03-bass-stem-midi-gp-implementation.md"
  ```

### Task 4: MIDI -> EADG tab mapping + GP5 export service (TDD)

**Files:**
- Create: `backend/app/tabs.py`
- Create: `backend/tests/test_tabs.py`
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Write failing tests for EADG mapping and GP export**
  - Validate mapped notes stay within 4-string EADG valid fret range.
  - Validate deterministic mapping for repeated input.
  - Validate exported bytes are parseable GP5 payload.

- [ ] **Step 2: Run RED test**
  - Run: `cd backend && uv run pytest tests/test_tabs.py -q`
  - Expected: `FAIL` (module missing).

- [ ] **Step 3: Implement minimal mapper + exporter**
  - Add:
    - `map_midi_to_eadg_positions(midi_bytes) -> list[TabNote]`
    - `build_gp5_from_tab_positions(tab_notes) -> bytes`
  - Use `PyGuitarPro` writer for GP5 output.

- [ ] **Step 4: Add dependency**
  - Add `pyguitarpro` package, sync lockfile.

- [ ] **Step 5: Run GREEN test**
  - Run: `cd backend && uv run pytest tests/test_tabs.py -q`
  - Expected: `PASS`.

- [ ] **Step 6: Commit**
  - Run:
  ```bash
  git add backend/app/tabs.py backend/tests/test_tabs.py backend/pyproject.toml backend/uv.lock
  git commit -m "feat(backend): add eadg midi to gp5 tab generator" -m "Refs: docs/plans/2026-03-03-bass-stem-midi-gp-implementation.md"
  ```

### Task 5: Pipeline integration for tab generation + artifact API endpoints (TDD)

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing tests for tab status and file endpoints**
  - Add tests for:
    - `tab_status`, `tab_error` in status payload
    - `GET /api/songs/{song_id}/midi/file`
    - `GET /api/songs/{song_id}/tabs/file`

- [ ] **Step 2: Run RED test**
  - Run: `cd backend && uv run pytest tests/test_api.py -q`
  - Expected: `FAIL`.

- [ ] **Step 3: Implement minimal backend changes**
  - Run tabs generation after MIDI stage.
  - Persist GP5 artifact.
  - Add metadata/file stream endpoints.

- [ ] **Step 4: Run GREEN test**
  - Run: `cd backend && uv run pytest tests/test_api.py -q`
  - Expected: `PASS`.

- [ ] **Step 5: Commit**
  - Run:
  ```bash
  git add backend/app/main.py backend/tests/test_api.py
  git commit -m "feat(api): add tab generation stage and artifact endpoints" -m "Refs: docs/plans/2026-03-03-bass-stem-midi-gp-implementation.md"
  ```

### Task 6: Frontend tab viewer + playback synchronization (TDD)

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/types.ts`
- Create: `frontend/src/components/TabViewerPanel.tsx`
- Create: `frontend/src/components/__tests__/TabViewerPanel.test.tsx`
- Create: `frontend/src/lib/__tests__/api.tabs.test.ts`

- [ ] **Step 1: Write failing frontend tests**
  - API client tests for tabs metadata/file URL helpers.
  - Component tests for render/fallback states.
  - Sync test asserting tab cursor updates from player time prop.

- [ ] **Step 2: Run RED tests**
  - Run: `cd frontend && bun run test`
  - Expected: `FAIL`.

- [ ] **Step 3: Implement minimal alphaTab integration**
  - Add alphaTab dependency.
  - Render GP tab panel when tab artifact exists.
  - Use existing transport time to drive tab cursor.

- [ ] **Step 4: Run GREEN tests**
  - Run: `cd frontend && bun run test`
  - Expected: `PASS`.

- [ ] **Step 5: Commit**
  - Run:
  ```bash
  git add frontend/package.json frontend/bun.lock frontend/src/App.tsx frontend/src/lib/api.ts frontend/src/lib/types.ts frontend/src/components/TabViewerPanel.tsx frontend/src/components/__tests__/TabViewerPanel.test.tsx frontend/src/lib/__tests__/api.tabs.test.ts
  git commit -m "feat(frontend): add gp tab viewer synced with playback clock" -m "Refs: docs/plans/2026-03-03-bass-stem-midi-gp-implementation.md"
  ```

### Task 7: Documentation, reset, and verification gate

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-03-03-bass-stem-midi-gp-implementation.md`

- [ ] **Step 1: Update README**
  - Add MIDI/tab pipeline, new endpoints, dependency notes (`basic-pitch`, `pyguitarpro`, `alphaTab`).

- [ ] **Step 2: Run full verification**
  - Run:
  ```bash
  cd backend && uv run pytest tests/ -v
  cd frontend && bun run test
  cd frontend && bun run build
  ```
  - Expected: all pass.

- [ ] **Step 3: Run fresh-state reset before final handoff**
  - Run: `make reset`
  - Expected: runtime state cleaned and recreated for verification flow.

- [ ] **Step 4: Final commit**
  - Run:
  ```bash
  git add README.md docs/plans/2026-03-03-bass-stem-midi-gp-implementation.md
  git commit -m "docs: add bass midi gp workflow and verification notes" -m "Refs: docs/plans/2026-03-03-bass-stem-midi-gp-implementation.md"
  ```
