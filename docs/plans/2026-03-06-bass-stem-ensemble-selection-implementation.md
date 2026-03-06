# Bass Stem Ensemble Selection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add opt-in multi-model bass analysis candidate execution, deterministic transcription-focused candidate scoring, and guitar-aware bleed cancellation on top of the existing analysis-stem architecture without changing playback stem behavior.

**Architecture:** Keep persisted user-facing stem separation on the existing single-model path, but extend the analysis-only path to run one or more Demucs models, refine each candidate analysis stem from its separated sources, score candidates with deterministic signal features, select the best model, and persist one final `bass_analysis.wav` plus compact diagnostics. Reuse each model’s separated stems for refinement and scoring so each candidate model is separated once and handled independently with graceful degradation.

**Tech Stack:** FastAPI backend, Python dataclasses/helpers, Demucs runner, numpy/scipy/librosa, pytest.

---

### Task 1: Create and checkpoint the implementation plan

**Files:**
- Create: `docs/plans/2026-03-06-bass-stem-ensemble-selection-implementation.md`

- [x] Step 1: Add the new implementation plan file under `docs/plans/`.
- [x] Step 2: Review the current stem-analysis and diagnostics flow and align task scopes with repo conventions.
- [x] Step 3: Commit the new plan file with the plan path referenced in the commit message.

### Task 2: Add RED tests for config parsing and ensemble orchestration

**Files:**
- Modify: `backend/tests/test_stems.py`

- [x] Step 1: Add failing tests for deterministic candidate-model parsing, deduplication, and new typed analysis config fields.
- [x] Step 2: Add failing tests proving ensemble mode runs multiple candidate models and default mode stays single-model.
- [x] Step 3: Add failing tests proving one candidate failure can be skipped and all-candidate failure is explicit and safe.
- [x] Step 4: Run targeted stem tests and confirm RED.
- [x] Step 5: Commit.

### Task 3: Implement typed config and candidate execution scaffolding

**Files:**
- Modify: `backend/app/stems.py`
- Modify: `backend/tests/test_stems.py`

- [x] Step 1: Extend `StemAnalysisConfig` with typed subtraction, gating, and selection/scoring settings.
- [x] Step 2: Add env parsing and validation for the new analysis tuning variables while preserving current defaults.
- [x] Step 3: Implement candidate-model execution helpers that separate once per model and record per-model availability/failure diagnostics.
- [x] Step 4: Run targeted stem tests and confirm GREEN for config/orchestration behavior.
- [x] Step 5: Commit.

### Task 4: Add RED tests for guitar-aware refinement and deterministic scoring

**Files:**
- Modify: `backend/tests/test_stems.py`

- [x] Step 1: Add failing tests proving guitar stems are used when available and weighted separately from `other`.
- [x] Step 2: Add failing tests proving scoring selects the best transcription candidate deterministically with component breakdowns.
- [x] Step 3: Add failing tests proving subtraction weights and gate settings influence refinement/scoring directionally.
- [x] Step 4: Run targeted stem tests and confirm RED.
- [x] Step 5: Commit.

### Task 5: Implement guitar-aware refinement, scoring, and candidate selection

**Files:**
- Modify: `backend/app/stems.py`
- Modify: `backend/tests/test_stems.py`

- [x] Step 1: Refactor analysis refinement into small pure helpers that can combine bass, other, and guitar bleed sources.
- [x] Step 2: Implement deterministic scoring components for transcription suitability and compact serializable per-candidate diagnostics.
- [x] Step 3: Select the best successful candidate, persist the winning `bass_analysis.wav`, and preserve graceful fallback behavior.
- [x] Step 4: Run targeted stem tests and confirm GREEN for refinement, scoring, and diagnostics.
- [x] Step 5: Commit.

### Task 6: Wire ensemble selection into the analysis-stem generation flow

**Files:**
- Modify: `backend/app/stems.py`
- Modify: `backend/tests/test_api.py`
- Modify: `backend/tests/test_midi.py` (if needed)

- [x] Step 1: Update the analysis-stem builder entry points to use ensemble selection only for analysis/high-accuracy mode.
- [x] Step 2: Preserve current playback/download stem behavior and existing public API responses while expanding diagnostics naturally.
- [x] Step 3: Add or adjust integration coverage only where the selected analysis artifact is externally observable.
- [x] Step 4: Run targeted tests and confirm GREEN for end-to-end analysis-stem selection behavior.
- [x] Step 5: Commit.

### Task 7: Update concise docs and env/config references

**Files:**
- Modify: `README.md` (if config is documented there)
- Modify: `docs/plans/2026-03-06-bass-stem-ensemble-selection-implementation.md`

- [x] Step 1: Document the new analysis ensemble and bleed-cancellation env knobs in the existing config style.
- [x] Step 2: Update the plan file to reflect completed task status accurately.
- [x] Step 3: Commit.

### Task 8: Verify, reset, and finalize

**Files:**
- Modify: `docs/plans/2026-03-06-bass-stem-ensemble-selection-implementation.md`

- [x] Step 1: Run targeted backend tests covering stems and any touched integration points.
- [x] Step 2: Run broader backend verification relevant to the changed flow.
- [x] Step 3: Run `make reset`.
- [x] Step 4: Re-run critical verification after reset.
- [x] Step 5: Mark all plan steps complete.
- [x] Step 6: Commit.
