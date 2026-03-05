# Phase 2 Bass Tab Quality Upgrade Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade bass tab generation quality using drums-driven rhythm grid, cleaned transcription, playable fingering optimization, and AlphaTex+sync output while persisting MIDI and tabs.

**Architecture:** Add modular backend services for rhythm extraction, cleanup, quantization, fingering, and AlphaTex export; compose them in a tab pipeline; expose a dedicated stems-to-tab endpoint and integrate the same pipeline in analyze flow. Persist MIDI to `song_midis` and AlphaTex to `song_tabs` with `tab_format='alphatex'`.

**Tech Stack:** Python 3.13+, FastAPI, LibSQL, Pytest, madmom, librosa fallback, mido, NumPy/SciPy, existing DeChord backend.

---

### Task 1: Add rhythm grid models and service scaffold (TDD)

**Files:**
- Create: `backend/app/services/rhythm_grid.py`
- Create: `backend/tests/test_rhythm_grid.py`
- Modify: `backend/app/main.py` (imports only if needed)

- [x] Step 1: Write failing tests for rhythm primitives (`Bar`, `BarGrid`, monotonic beat validation).
- [x] Step 2: Run test to verify RED.
  - Run: `cd backend && uv run pytest tests/test_rhythm_grid.py -q`
- [x] Step 3: Implement minimal models and monotonic validation.
- [x] Step 4: Run test to verify GREEN.
- [x] Step 5: Commit.
  - `git commit -m "feat(rhythm): add bar grid primitives" -m "Refs: docs/plans/2026-03-04-phase2-bass-tab-quality-implementation.md"`

### Task 2: Implement beat/downbeat extraction with fallback and BPM reconciliation (TDD)

**Files:**
- Modify: `backend/app/services/rhythm_grid.py`
- Modify: `backend/tests/test_rhythm_grid.py`

- [x] Step 1: Write failing tests for madmom path abstraction, librosa fallback path, and tempo ambiguity correction (x2/x0.5).
- [x] Step 2: Run RED tests for new behaviors.
- [x] Step 3: Implement extraction adapters and `tempo_used` reconciliation logic.
- [x] Step 4: Run GREEN tests.
- [x] Step 5: Commit.
  - `git commit -m "feat(rhythm): add beat tracking fallback and bpm reconciliation" -m "Refs: docs/plans/2026-03-04-phase2-bass-tab-quality-implementation.md"`

### Task 3: Add bass transcriber interface and adapter around existing MIDI path (TDD)

**Files:**
- Create: `backend/app/services/bass_transcriber.py`
- Modify: `backend/app/midi.py`
- Create: `backend/tests/test_bass_transcriber.py`

- [x] Step 1: Write failing tests for transcriber contract returning raw notes with confidence and MIDI bytes.
- [x] Step 2: Run RED tests.
- [x] Step 3: Implement `BassTranscriber` protocol and `BasicPitchTranscriber` adapter using existing transcription path.
- [x] Step 4: Run GREEN tests.
- [x] Step 5: Commit.
  - `git commit -m "feat(transcriber): add bass transcriber interface" -m "Refs: docs/plans/2026-03-04-phase2-bass-tab-quality-implementation.md"`

### Task 4: Implement note cleanup service (TDD)

**Files:**
- Create: `backend/app/services/note_cleanup.py`
- Create: `backend/tests/test_note_cleanup.py`

- [x] Step 1: Write failing tests for overlap resolution, short-note/confidence filtering, repeated-note merge, octave jump smoothing heuristic.
- [x] Step 2: Run RED tests.
- [x] Step 3: Implement minimal cleanup passes to satisfy tests.
- [x] Step 4: Run GREEN tests.
- [x] Step 5: Commit.
  - `git commit -m "feat(cleanup): add bass note cleanup pipeline" -m "Refs: docs/plans/2026-03-04-phase2-bass-tab-quality-implementation.md"`

### Task 5: Implement beat-grid quantization and bar-boundary splitting (TDD)

**Files:**
- Create: `backend/app/services/quantization.py`
- Create: `backend/tests/test_quantization.py`
- Modify: `backend/app/services/rhythm_grid.py` (if shared helpers needed)

- [x] Step 1: Write failing tests for 1/16 snapping error bounds and splitting cross-bar notes.
- [x] Step 2: Run RED tests.
- [x] Step 3: Implement quantizer with bar-local beat position mapping.
- [x] Step 4: Run GREEN tests.
- [x] Step 5: Commit.
  - `git commit -m "feat(quantization): snap bass notes to drums bar grid" -m "Refs: docs/plans/2026-03-04-phase2-bass-tab-quality-implementation.md"`

### Task 6: Implement DP fingering optimizer (TDD)

**Files:**
- Create: `backend/app/services/fingering.py`
- Create: `backend/tests/test_fingering.py`

- [x] Step 1: Write failing tests ensuring valid candidate constraints and reduced extreme fret jumps.
- [x] Step 2: Run RED tests.
- [x] Step 3: Implement candidate generation and DP cost optimization.
- [x] Step 4: Run GREEN tests.
- [x] Step 5: Commit.
  - `git commit -m "feat(fingering): add dynamic-programming bass fingering" -m "Refs: docs/plans/2026-03-04-phase2-bass-tab-quality-implementation.md"`

### Task 7: Implement AlphaTex exporter with `\sync` markers (TDD)

**Files:**
- Create: `backend/app/services/alphatex_exporter.py`
- Create: `backend/tests/test_alphatex_exporter.py`

- [x] Step 1: Write failing tests for score header, tuning, bar serialization, and sync rules (bar 0, every 8 bars, last bar).
- [x] Step 2: Run RED tests.
- [x] Step 3: Implement exporter and sync-point generation.
- [x] Step 4: Run GREEN tests.
- [x] Step 5: Commit.
  - `git commit -m "feat(alphatex): export bass tabs with sync points" -m "Refs: docs/plans/2026-03-04-phase2-bass-tab-quality-implementation.md"`

### Task 8: Compose end-to-end tab pipeline service (TDD)

**Files:**
- Create: `backend/app/services/tab_pipeline.py`
- Create: `backend/tests/test_tab_pipeline.py`

- [x] Step 1: Write failing integration-style unit tests for stage composition and debug counters.
- [x] Step 2: Run RED tests.
- [x] Step 3: Implement orchestrator composing rhythm/transcribe/cleanup/quantize/fingering/export.
- [x] Step 4: Run GREEN tests.
- [x] Step 5: Commit.
  - `git commit -m "feat(pipeline): compose phase2 bass tab generation pipeline" -m "Refs: docs/plans/2026-03-04-phase2-bass-tab-quality-implementation.md"`

### Task 9: Add `POST /api/tab/from-demucs-stems` endpoint and persistence wiring (TDD)

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`
- Modify: `backend/app/db_schema.sql` (only if metadata fields need extension)

- [x] Step 1: Write failing API tests for request validation, success payload, and error responses.
- [x] Step 2: Run RED tests.
- [x] Step 3: Implement endpoint, MIDI persistence in `song_midis`, AlphaTex persistence in `song_tabs` (`tab_format='alphatex'`).
- [x] Step 4: Run GREEN tests.
- [x] Step 5: Commit.
  - `git commit -m "feat(api): add stems-to-alphatex tab generation endpoint" -m "Refs: docs/plans/2026-03-04-phase2-bass-tab-quality-implementation.md"`

### Task 10: Integrate phase2 pipeline into `/api/analyze` stems flow (TDD)

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

- [x] Step 1: Write failing tests asserting `/api/analyze` persists AlphaTex tabs and updated status fields remain coherent.
- [x] Step 2: Run RED tests.
- [x] Step 3: Replace GP5 generation path with phase2 pipeline call and AlphaTex persistence.
- [x] Step 4: Run GREEN tests.
- [x] Step 5: Commit.
  - `git commit -m "feat(api): route analyze stems tab generation through phase2 pipeline" -m "Refs: docs/plans/2026-03-04-phase2-bass-tab-quality-implementation.md"`

### Task 11: Update tab artifact serving/downloading for AlphaTex-only local workflow (TDD)

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

- [x] Step 1: Write failing tests for `/api/songs/{id}/tabs/file` and `/tabs/download` returning AlphaTex bytes with proper content headers/extensions.
- [x] Step 2: Run RED tests.
- [x] Step 3: Implement AlphaTex response media type and `.alphatex` download naming.
- [x] Step 4: Run GREEN tests.
- [x] Step 5: Commit.
  - `git commit -m "feat(api): serve alphatex tab artifacts" -m "Refs: docs/plans/2026-03-04-phase2-bass-tab-quality-implementation.md"`

### Task 12: Documentation + verification + fresh-state reset (TDD completion gate)

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-03-04-phase2-bass-tab-quality-implementation.md`

- [x] Step 1: Update docs for new endpoint, AlphaTex format, and phase2 pipeline behavior.
- [x] Step 2: Run backend targeted suites and full test suite.
  - `cd backend && uv run pytest tests/test_rhythm_grid.py tests/test_note_cleanup.py tests/test_quantization.py tests/test_fingering.py tests/test_alphatex_exporter.py tests/test_tab_pipeline.py tests/test_api.py -v`
  - `cd backend && uv run pytest tests -v`
- [x] Step 3: Run `make reset` before final verification/handoff.
- [x] Step 4: Re-run critical API tests after reset.
- [x] Step 5: Mark completed tasks as `[x]` in this plan and commit.
  - `git commit -m "docs: finalize phase2 tab quality verification and reset evidence" -m "Refs: docs/plans/2026-03-04-phase2-bass-tab-quality-implementation.md"`

---

## Execution Notes

- Required method: subagent-driven development + TDD for all implementation tasks.
- If a specific task cannot use subagents or TDD, pause and explicitly document why before proceeding.
- Do not skip task checkbox updates; this plan file is execution source of truth.
