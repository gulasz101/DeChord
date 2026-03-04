# Bass Fingering Root Cause Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix fingering octave mapping and solver behavior so playable bass notes survive to AlphaTex output, with hard safety checks and regression tests.

**Architecture:** Update fingering internals to correct MIDI tuning and partial-drop behavior, add debug probes and pipeline/export guardrails, then validate with targeted unit and integration tests plus refreshed debug report evidence.

**Tech Stack:** Python 3.13+, FastAPI, Pytest, existing `backend/app/services/*` phase2 pipeline.

---

### Task 1: Add failing tests for fingering candidate generation regression

**Files:**
- Modify: `backend/tests/test_fingering.py`
- Modify: `backend/app/services/fingering.py` (imports only if test needs explicit helper export)

- [x] Step 1: Write failing candidate tests for corrected bass tuning behavior.
  - Cases: `pitch=34 -> (3,1)`, `33 -> (3,0)`, `40 includes (4,12)`, `62 -> (1,19)`, `20 -> []`.
- [x] Step 2: Run tests to verify RED.
  - Run: `cd backend && uv run pytest tests/test_fingering.py -q`
  - Expected: FAIL on candidate assertions with current octave-high tuning.
- [x] Step 3: Commit failing test-first state.
  - `git add backend/tests/test_fingering.py`
  - `git commit -m "test(fingering): add octave regression candidate cases" -m "Refs: docs/plans/2026-03-04-bass-fingering-root-cause-fix-implementation.md"`

### Task 2: Implement tuning fix and explicit naming in fingering solver

**Files:**
- Modify: `backend/app/services/fingering.py`
- Modify: `backend/tests/test_fingering.py`

- [x] Step 1: Replace tuning map with `STANDARD_BASS_TUNING_MIDI = {4: 28, 3: 33, 2: 38, 1: 43}` and keep string-order semantics.
- [x] Step 2: Ensure candidate generation function uses `_MIDI`-named constant and deterministic ordering.
- [x] Step 3: Run fingering tests to verify GREEN for candidate cases.
  - Run: `cd backend && uv run pytest tests/test_fingering.py -q`
- [x] Step 4: Commit implementation.
  - `git add backend/app/services/fingering.py backend/tests/test_fingering.py`
  - `git commit -m "fix(fingering): correct standard bass tuning midi map" -m "Refs: docs/plans/2026-03-04-bass-fingering-root-cause-fix-implementation.md"`

### Task 3: Add failing test for partial unplayable note handling (no all-or-nothing collapse)

**Files:**
- Modify: `backend/tests/test_fingering.py`

- [ ] Step 1: Add test with playable-unplayable-playable sequence (e.g. `40, 20, 45`) expecting playable notes retained.
- [ ] Step 2: Run test to verify RED against current all-or-nothing behavior.
  - Run: `cd backend && uv run pytest tests/test_fingering.py::test_optimize_fingering_drops_only_unplayable_notes -q`
  - Expected: FAIL because solver currently returns empty.
- [ ] Step 3: Commit failing test-first state.
  - `git add backend/tests/test_fingering.py`
  - `git commit -m "test(fingering): add partial-unplayable retention case" -m "Refs: docs/plans/2026-03-04-bass-fingering-root-cause-fix-implementation.md"`

### Task 4: Implement robust solver + debug counters + hard-disabled octave salvage plumbing

**Files:**
- Modify: `backend/app/services/fingering.py`
- Modify: `backend/app/services/tab_pipeline.py`
- Modify: `backend/tests/test_fingering.py`
- Modify: `backend/tests/test_tab_pipeline.py`

- [ ] Step 1: Refactor fingering solve path to drop only per-note failures and preserve playable notes.
- [ ] Step 2: Keep octave-salvage code path hard-disabled and expose `octave_salvaged_notes=0` in debug flow.
- [ ] Step 3: Add dropped reason counting (`no_fingering_candidate`) and surfaced tuning/max-fret metadata for debug.
- [ ] Step 4: Run target tests to verify GREEN.
  - Run: `cd backend && uv run pytest tests/test_fingering.py tests/test_tab_pipeline.py -q`
- [ ] Step 5: Commit implementation.
  - `git add backend/app/services/fingering.py backend/app/services/tab_pipeline.py backend/tests/test_fingering.py backend/tests/test_tab_pipeline.py`
  - `git commit -m "fix(fingering): keep playable notes when some notes are unplayable" -m "Refs: docs/plans/2026-03-04-bass-fingering-root-cause-fix-implementation.md"`

### Task 5: Add debug-only candidate sanity probe and failing tests

**Files:**
- Modify: `backend/app/services/fingering.py`
- Modify: `backend/tests/test_fingering.py`

- [ ] Step 1: Add failing tests for debug probe success conditions and explicit failure signaling.
- [ ] Step 2: Run RED tests.
  - Run: `cd backend && uv run pytest tests/test_fingering.py -q`
- [ ] Step 3: Commit failing test-first state.
  - `git add backend/tests/test_fingering.py`
  - `git commit -m "test(fingering): add debug probe coverage for canonical pitches" -m "Refs: docs/plans/2026-03-04-bass-fingering-root-cause-fix-implementation.md"`

### Task 6: Implement pipeline/export guardrail for rests-only failure mode

**Files:**
- Modify: `backend/app/services/tab_pipeline.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_tab_pipeline.py`
- Modify: `backend/tests/test_api.py`

- [ ] Step 1: Add guard that raises explicit error when quantized notes exist but fingered notes are zero.
- [ ] Step 2: Ensure API returns structured error/debug payload including stage counters, reasons, and tuning values.
- [ ] Step 3: Add/adjust tests to assert no silent successful rests-only export.
- [ ] Step 4: Run API and pipeline tests to verify GREEN.
  - Run: `cd backend && uv run pytest tests/test_tab_pipeline.py tests/test_api.py -q`
- [ ] Step 5: Commit implementation.
  - `git add backend/app/services/tab_pipeline.py backend/app/main.py backend/tests/test_tab_pipeline.py backend/tests/test_api.py`
  - `git commit -m "fix(pipeline): fail fast when fingering drops all quantized notes" -m "Refs: docs/plans/2026-03-04-bass-fingering-root-cause-fix-implementation.md"`

### Task 7: Add end-to-end smoke coverage for AlphaTex containing notes and sync lines

**Files:**
- Modify: `backend/tests/test_tab_pipeline.py`
- Modify: `backend/tests/test_alphatex_exporter.py` (if needed)

- [ ] Step 1: Add synthetic in-range notes smoke test asserting `after_fingering > 0`, note tokens exist, and `\\sync` entries remain.
- [ ] Step 2: Run RED then GREEN.
  - Run: `cd backend && uv run pytest tests/test_tab_pipeline.py tests/test_alphatex_exporter.py -q`
- [ ] Step 3: Commit tests + any minimal implementation updates.
  - `git add backend/tests/test_tab_pipeline.py backend/tests/test_alphatex_exporter.py backend/app/services/tab_pipeline.py backend/app/services/alphatex_exporter.py`
  - `git commit -m "test(pipeline): add alphatex non-rest smoke verification" -m "Refs: docs/plans/2026-03-04-bass-fingering-root-cause-fix-implementation.md"`

### Task 8: Regenerate debug report, run full verification, reset runtime, and finalize plan checkboxes

**Files:**
- Modify: `DEBUG_REPORT.md`
- Modify: `docs/plans/2026-03-04-bass-fingering-root-cause-fix-implementation.md`

- [ ] Step 1: Re-run the same debug workflow on the same failing song and regenerate report evidence.
  - Must include updated tuning table, non-zero `after_fingering`/`exported_notes`, sample `string,fret`, and AlphaTex excerpt with notes.
- [ ] Step 2: Run targeted suites and full backend tests.
  - `cd backend && uv run pytest tests/test_fingering.py tests/test_tab_pipeline.py tests/test_alphatex_exporter.py tests/test_api.py -v`
  - `cd backend && uv run pytest tests -v`
- [ ] Step 3: Run fresh-state reset before final verification.
  - `make reset`
- [ ] Step 4: Re-run critical tests post-reset.
  - `cd backend && uv run pytest tests/test_fingering.py tests/test_tab_pipeline.py tests/test_api.py -v`
- [ ] Step 5: Mark all completed tasks `[x]` in this plan file.
- [ ] Step 6: Commit verification artifacts and plan completion state.
  - `git add DEBUG_REPORT.md docs/plans/2026-03-04-bass-fingering-root-cause-fix-implementation.md`
  - `git commit -m "docs: capture fingering fix debug evidence and verification" -m "Refs: docs/plans/2026-03-04-bass-fingering-root-cause-fix-implementation.md"`

---

## Execution Notes

- Required method for implementation: subagent-driven development + strict TDD.
- If any task cannot use subagent-driven development or TDD, pause and explicitly document why before continuing.
- Keep this plan as execution source of truth: every task starts `[ ]` and is marked `[x]` only when complete.
