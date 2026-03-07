# Bass Stem Ensemble Correction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Correct the analysis-stem ensemble path so high-accuracy mode performs true per-model separations, scores each candidate deterministically, uses guitar-aware bleed cancellation when present, and proves those behaviors with tests.

**Architecture:** Keep standard analysis mode on the existing single-stem path, but route high-accuracy analysis through an explicit ensemble selector that runs Demucs once per candidate model, refines each candidate from that model’s own separated stems, scores the candidates, and persists the selected analysis stem with compact diagnostics. Wire the job flow to opt into this only for high-accuracy modes so normal playback and standard-speed transcription remain unchanged.

**Tech Stack:** FastAPI backend, Python dataclasses/helpers, Demucs runner, numpy/scipy, pytest.

---

### Task 1: Create and checkpoint the correction plan

**Files:**
- Create: `docs/plans/2026-03-06-bass-stem-ensemble-correction-implementation.md`

- [x] Step 1: Add the correction plan file under `docs/plans/`.
- [x] Step 2: Review the current ensemble path and note the corrective scope.
- [x] Step 3: Commit the plan with the plan path referenced in the commit message.

### Task 2: Add RED tests for true per-model separation behavior

**Files:**
- Modify: `backend/tests/test_stems.py`
- Modify: `backend/tests/test_api.py`

- [x] Step 1: Add failing tests proving ensemble mode re-separates every candidate model, including the configured primary model, even when standard stems are already available.
- [x] Step 2: Add failing tests proving standard mode keeps the current single-stem behavior and does not invoke extra candidate separations.
- [x] Step 3: Add failing tests proving high-accuracy job flow opts into ensemble analysis while standard mode does not.
- [x] Step 4: Run targeted tests and confirm RED.
- [x] Step 5: Commit.

### Task 3: Implement explicit ensemble orchestration and high-accuracy wiring

**Files:**
- Modify: `backend/app/stems.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_stems.py`
- Modify: `backend/tests/test_api.py`

- [x] Step 1: Add an explicit analysis candidate orchestration path that separates once per candidate model and reuses that candidate’s stems for refinement and scoring.
- [x] Step 2: Keep standard mode on the existing single-model/supplied-stem path for speed and compatibility.
- [x] Step 3: Wire high-accuracy analysis jobs to opt into ensemble selection without changing public API responses.
- [x] Step 4: Run targeted tests and confirm GREEN.
- [x] Step 5: Commit.

### Task 4: Add RED tests for scoring and guitar-aware diagnostics proof

**Files:**
- Modify: `backend/tests/test_stems.py`

- [x] Step 1: Add failing tests proving per-candidate score breakdowns are emitted for all successful candidates.
- [x] Step 2: Add failing tests proving guitar-assisted refinement changes the winning candidate when guitar bleed is the deciding contaminant.
- [x] Step 3: Add failing tests proving diagnostics record stem availability, weights used, and degradation reasons compactly per candidate.
- [x] Step 4: Run targeted tests and confirm RED.
- [x] Step 5: Commit.

### Task 5: Tighten scoring/refinement diagnostics and candidate proof points

**Files:**
- Modify: `backend/app/stems.py`
- Modify: `backend/tests/test_stems.py`

- [x] Step 1: Ensure candidate diagnostics expose compact scoring components, stem availability, subtract weights, selected flag, and degradation/failure reasons.
- [x] Step 2: Ensure guitar-aware cancellation is considered independently from generic `other` bleed in refinement and scoring.
- [x] Step 3: Run targeted tests and confirm GREEN.
- [x] Step 4: Commit.

### Task 6: Verify, reset, and finalize

**Files:**
- Modify: `docs/plans/2026-03-06-bass-stem-ensemble-correction-implementation.md`

- [x] Step 1: Run targeted backend tests for stems and API flow.
- [x] Step 2: Run broader backend verification relevant to the changed flow.
- [x] Step 3: Run `make reset`.
- [x] Step 4: Re-run critical verification after reset.
- [x] Step 5: Mark all plan steps complete.
- [x] Step 6: Commit.
